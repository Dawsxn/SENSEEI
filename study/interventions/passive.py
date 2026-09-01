"""The passive control arm: the same text, read with no tool at all.

Section 4.6.2's third arm. It receives the identical expository text and the
identical 40 minutes, and nothing else. It is the floor the two AI-assisted arms
are measured against, and it is what separates "SENSEE-I beats unguided chat"
from "any support beats none".

Its exclusion criterion is the only one that cannot be met by talking to
something: Section 4.6.3 excludes a passive participant who "advances to the
post-test before a realistic minimum reading time has elapsed". Since the phase
engine already holds every participant for the full period, nobody can advance
early — so what actually needs recording is whether the time was spent on the
reading at all.

Hence two measures rather than one:

- **Time with the text open**, which is not the same as time in the phase. A
  participant who closes the reading at minute six and stares at the wall has the
  same phase duration as one who reads throughout.
- **How far down the text they got**, from scroll position. Someone who never
  scrolled past the first screen did not read a text that runs to several.

Neither is proof of reading. Together they are the best evidence available
without eye-tracking, and they are the raw quantities the empirically-derived
threshold will be set against.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass(frozen=True)
class ScrollSample:
    """How far down the text the participant had reached, at one moment."""

    at: datetime
    #: 0.0 at the top, 1.0 at the bottom of the text.
    depth: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.depth <= 1.0:
            raise ValueError(f"Scroll depth must be within 0..1, got {self.depth}")


@dataclass(frozen=True)
class PassiveTelemetry:
    """The raw quantities the passive-arm exclusion criterion draws on (§4.6.3)."""

    participant_id: str
    started_at: datetime
    ended_at: datetime | None

    #: Time with the reading actually open, excluding any interval where the
    #: participant had navigated away.
    time_on_text: timedelta

    #: Furthest point reached in the text, 0..1.
    max_scroll_depth: float

    #: How many times they left the reading and came back.
    away_count: int

    #: Number of scroll observations. A session with almost none suggests either
    #: a very short text on screen or a participant who never moved.
    sample_count: int


class PassiveSession:
    """One participant's 40 minutes with the text and nothing else.

    Time on text is accumulated from explicit open/away events rather than
    inferred from the phase duration, because the two answer different questions
    and only one of them is evidence of engagement.
    """

    def __init__(self, participant_id: str, started_at: datetime):
        self.participant_id = participant_id
        self.started_at = started_at
        self.ended_at: datetime | None = None

        self._samples: list[ScrollSample] = []
        self._accumulated = timedelta()
        self._open_since: datetime | None = started_at
        self._away_count = 0

    @property
    def is_open(self) -> bool:
        return self._open_since is not None

    def went_away(self, at: datetime) -> None:
        """The participant left the reading — tab hidden, window blurred.

        Idempotent: a browser can fire the same event twice, and counting that as
        two departures would overstate how distracted someone was.
        """
        if self._open_since is None:
            return
        self._accumulated += self._elapsed_since(self._open_since, at)
        self._open_since = None
        self._away_count += 1

    def came_back(self, at: datetime) -> None:
        """The participant returned to the reading. Idempotent, as above."""
        if self._open_since is not None:
            return
        self._open_since = at

    def scrolled(self, depth: float, at: datetime) -> ScrollSample:
        """Record how far down the text the participant has reached."""
        sample = ScrollSample(at=at, depth=depth)
        self._samples.append(sample)
        return sample

    def close(self, at: datetime) -> None:
        """End the session when the intervention period does."""
        if self.ended_at is not None:
            return
        if self._open_since is not None:
            self._accumulated += self._elapsed_since(self._open_since, at)
            self._open_since = None
        self.ended_at = at

    def time_on_text(self, now: datetime | None = None) -> timedelta:
        """Time with the reading open, including the interval still in progress."""
        total = self._accumulated
        if self._open_since is not None and now is not None:
            total += self._elapsed_since(self._open_since, now)
        return total

    def telemetry(self) -> PassiveTelemetry:
        return PassiveTelemetry(
            participant_id=self.participant_id,
            started_at=self.started_at,
            ended_at=self.ended_at,
            time_on_text=self._accumulated,
            max_scroll_depth=max((s.depth for s in self._samples), default=0.0),
            away_count=self._away_count,
            sample_count=len(self._samples),
        )

    # --- persistence ------------------------------------------------------

    def snapshot(self) -> dict:
        """Everything needed to reconstruct this reading session exactly.

        The accumulated total and the open interval are stored separately, so a
        participant who is mid-read when the server restarts keeps both the time
        already banked and the fact that their clock is still running.
        """
        return {
            "participant_id": self.participant_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "accumulated_seconds": self._accumulated.total_seconds(),
            "open_since": self._open_since.isoformat() if self._open_since else None,
            "away_count": self._away_count,
            "samples": [
                {"at": s.at.isoformat(), "depth": s.depth} for s in self._samples
            ],
        }

    @classmethod
    def restore(cls, data: dict) -> PassiveSession:
        from ..phases import parse_time

        session = cls(
            participant_id=data["participant_id"],
            started_at=parse_time(data["started_at"]),
        )
        session.ended_at = parse_time(data.get("ended_at"))
        session._accumulated = timedelta(seconds=data.get("accumulated_seconds", 0))
        session._open_since = parse_time(data.get("open_since"))
        session._away_count = int(data.get("away_count", 0))
        session._samples = [
            ScrollSample(at=parse_time(s["at"]), depth=float(s["depth"]))
            for s in data.get("samples", [])
        ]
        return session

    @staticmethod
    def _elapsed_since(start: datetime, end: datetime) -> timedelta:
        """Elapsed time, never negative.

        These events come from a browser, where a clock adjustment or an event
        arriving out of order can put ``end`` before ``start``. Clamping to zero
        keeps a stray event from inflating time on text, which is precisely the
        quantity an excluded participant would need to inflate.
        """
        return max(end - start, timedelta())
