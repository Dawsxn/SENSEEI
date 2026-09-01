"""The one seam between this harness and the SENSEE-I application.

The SENSEE-I application is built and owned separately. This harness must not
import it, query it ad hoc from a dozen places, or assume anything about its
internals — otherwise every change over there breaks the trial tooling over here,
and the two have to be developed in lockstep by people working to different
deadlines.

So everything the harness needs from the app passes through the ``SenseeiLink``
protocol below, and that is a deliberately small surface. Exactly three things
are needed:

1. **Where to send a participant** so they can do their tutoring session.
2. **What happened in that session**, after the fact, for the exclusion criteria
   of Section 4.6.3 (session time, conversational turns) and for the export.
3. **How to delete it**, when a participant withdraws (Section 4.7.1).

Notice what is *not* here. The harness never asks the app to start a session for
it, never asks the app to enforce the 40-minute clock, and never advances a phase
because the app said so. The phase engine owns all of that (see ``phases.py``),
which is why the harness can run its full sequence with a fake link, before the
application exists at all.

**Implementations**

- :class:`FakeSenseeiLink` — synthetic sessions. Lets the whole harness be built,
  tested, and dry-run end to end today.
- A read-only database link, once the app has a schema. All knowledge of the
  app's tables belongs in that one class, so an app migration costs one file's
  worth of edits here rather than a hunt through the harness.

**What the app is asked to provide** (each has a fallback, none is a large ask):

- A read-only role or a couple of read-only endpoints exposing the fields of
  :class:`SenseeiTelemetry`.
- Sessions that survive a page reload for study participants. The app's normal
  rule discards an abandoned session; in a supervised lab that means one stray
  browser refresh destroys a participant's forty minutes and costs a data point
  that cannot be recovered.
- A way to delete one participant's sessions.
- ``rubric_version``, ``prompt_version`` and ``model`` stamped on every session,
  which the app's own data model already calls for. Without them a prompt change
  partway through collection is invisible in the data.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

#: Arbitrary fixed start time for synthetic sessions, so a fake run is stable.
_FAKE_EPOCH = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class SenseeiTelemetry:
    """What one SENSEE-I tutoring session did, as the harness needs to see it.

    This is the harness's own vocabulary, not the app's. It exists so that a
    rename or restructure in the app changes one mapping rather than every
    consumer.
    """

    session_id: str

    started_at: datetime
    ended_at: datetime | None

    #: "complete", "fallback", or "unfinished" — the last covering a session cut
    #: off when the intervention period expired mid-step (§4.6.2).
    status: str

    #: Conversational turns, counting each student submission. One of the two
    #: quantities the SENSEE-I exclusion criterion is derived from (§4.6.3).
    turn_count: int

    #: The furthest SEE-I step reached: State, Elaborate, Exemplify, Illustrate.
    #: Under intention-to-treat this never excludes anyone; it is reported.
    highest_step: str

    #: Attempts spent on each step, keyed by step name.
    attempts_per_step: dict[str, int] = field(default_factory=dict)

    #: Every criterion the Assessment Agent flagged as failing, across the
    #: session. Descriptive; also the closest thing the trial has to a window
    #: into where understanding broke down.
    failed_criteria: tuple[str, ...] = ()

    #: Provenance. Two sessions graded under different rubric or prompt versions
    #: are not the same experience, and without these there is no way to tell
    #: them apart afterwards.
    rubric_version: str | None = None
    prompt_version: str | None = None
    model: str | None = None

    @property
    def duration(self) -> timedelta | None:
        """Wall-clock session length, the other half of the exclusion criterion."""
        if self.ended_at is None:
            return None
        return self.ended_at - self.started_at

    @property
    def total_attempts(self) -> int:
        return sum(self.attempts_per_step.values())


@runtime_checkable
class SenseeiLink(Protocol):
    """Everything the harness is allowed to know about the SENSEE-I application."""

    def session_url(self, participant_id: str) -> str:
        """Where to send this participant for their tutoring session."""
        ...

    def fetch_telemetry(self, participant_id: str) -> SenseeiTelemetry | None:
        """What that participant's session did, or None if they never started one.

        Called after the intervention, not during it. Nothing in the harness's
        pacing depends on this answering, or on it answering promptly.
        """
        ...

    def delete_participant_data(self, participant_id: str) -> int:
        """Erase this participant's app-side session data. Returns rows removed.

        Required by the right to withdraw (§4.7.1) and by the end-of-retention
        deletion (§4.6.6). Deleting the harness's own records is not enough while
        transcripts remain in the app.
        """
        ...


class FakeSenseeiLink:
    """A stand-in that behaves plausibly, so the harness can be built without the app.

    Every value is derived deterministically from the participant identifier, so
    a given participant produces the same session on every run. That matters for
    tests, and it matters for the full dry run: the export can be generated,
    inspected, and checked for missing fields long before a real session exists
    to generate it from.

    It is a development tool. It must never be the configured link during a pilot
    or during collection, and the harness refuses to start a real run with it.
    """

    #: Marks this implementation as unfit for real data collection.
    is_synthetic = True

    def __init__(
        self,
        base_url: str = "https://senseei.example/session",
        started_at: datetime | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._started_at = started_at
        self._deleted: set[str] = set()

    def _seed(self, participant_id: str) -> int:
        digest = hashlib.sha256(participant_id.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big")

    def session_url(self, participant_id: str) -> str:
        return f"{self.base_url}/{participant_id}"

    def fetch_telemetry(self, participant_id: str) -> SenseeiTelemetry | None:
        if participant_id in self._deleted:
            return None

        seed = self._seed(participant_id)
        steps = ("State", "Elaborate", "Exemplify", "Illustrate")

        # How far they got, and how hard each step was. Spread across the range
        # so that a dry run exercises completions, fallbacks, and cut-offs rather
        # than one happy path.
        reached = seed % 4
        status = ("fallback", "unfinished", "complete", "complete")[reached]
        attempts = {
            steps[i]: 1 + ((seed >> (3 * i)) % 3) for i in range(reached + 1)
        }
        failed = tuple(
            f"{step}:criterion-{(seed >> i) % 4}"
            for i, (step, tries) in enumerate(attempts.items())
            if tries > 1
        )

        started = self._started_at or _FAKE_EPOCH
        minutes = 8 + (seed % 32)

        return SenseeiTelemetry(
            session_id=f"fake-{participant_id}",
            started_at=started,
            ended_at=started + timedelta(minutes=minutes),
            status=status,
            turn_count=sum(attempts.values()),
            highest_step=steps[reached],
            attempts_per_step=attempts,
            failed_criteria=failed,
            rubric_version="rubric_v3",
            prompt_version="system_prompt_v3",
            model="fake-model",
        )

    def delete_participant_data(self, participant_id: str) -> int:
        if participant_id in self._deleted:
            return 0
        self._deleted.add(participant_id)
        return 1
