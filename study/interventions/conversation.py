"""The transcript of one unguided-LLM session, and what is measured from it.

Section 4.6.3 excludes an unguided-arm participant whose "session length or total
word input falls below a minimum threshold indicating genuine engagement with the
tool". Both quantities are properties of the transcript, so the transcript is the
record and the measures are derived from it rather than counted as they go. That
way a recount after the fact — with a revised definition of a word, say — is
possible, which matters because the thresholds themselves are not set until the
pilot has run.

The transcript is also data in its own right. It is the only window into what
unguided use actually looked like for these participants, which is the behaviour
Section 2.1 characterises and this arm exists to represent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

#: A word is a run of characters separated by whitespace. Deliberately the
#: simplest defensible rule: it is transparent, it is what a participant would
#: get from a word counter, and any cleverer definition would need defending in
#: the write-up for no gain in what it measures.
_WORD = re.compile(r"\S+")


def count_words(text: str) -> int:
    return len(_WORD.findall(text))


class Speaker(str, Enum):
    PARTICIPANT = "participant"
    MODEL = "model"


@dataclass(frozen=True)
class Turn:
    """One message. Model turns may record a failure instead of a reply."""

    speaker: Speaker
    text: str
    at: datetime

    #: Set on a model turn the provider never delivered. The participant's own
    #: message is still kept: their words are the measured quantity, and losing
    #: them to a network error would quietly deflate their engagement score.
    error: str | None = None

    @property
    def failed(self) -> bool:
        return self.error is not None

    @property
    def word_count(self) -> int:
        return count_words(self.text)


@dataclass
class Conversation:
    """Everything one participant said to the model, and it back to them."""

    participant_id: str
    started_at: datetime
    turns: list[Turn] = field(default_factory=list)
    ended_at: datetime | None = None

    def add(self, turn: Turn) -> Turn:
        if self.ended_at is not None:
            raise ConversationClosed(
                f"Conversation for {self.participant_id} is already closed."
            )
        if self.turns and turn.at < self.turns[-1].at:
            raise ValueError("Turns must be recorded in order.")
        self.turns.append(turn)
        return turn

    def close(self, at: datetime) -> None:
        """Close the transcript at the end of the intervention period."""
        if self.ended_at is None:
            self.ended_at = at

    # --- the measured quantities -----------------------------------------

    @property
    def participant_turns(self) -> list[Turn]:
        return [t for t in self.turns if t.speaker is Speaker.PARTICIPANT]

    @property
    def turn_count(self) -> int:
        """Messages the participant sent. One half of the exclusion criterion."""
        return len(self.participant_turns)

    @property
    def word_count(self) -> int:
        """Words the participant typed, across the whole session.

        Counts only what the participant wrote. The model's output is not
        engagement — a session of one lazy question and four screens of generated
        prose is precisely the pattern this arm is meant to be able to show.
        """
        return sum(t.word_count for t in self.participant_turns)

    @property
    def duration(self) -> timedelta | None:
        """Session length. The other half of the exclusion criterion."""
        if self.ended_at is None:
            return None
        return self.ended_at - self.started_at

    @property
    def failed_replies(self) -> int:
        """Model turns lost to provider errors.

        Worth watching during the run rather than only afterwards: a rising count
        across participants is the signature of a saturated rate limit, and in a
        single-sitting trial that is the failure mode with no recovery.
        """
        return sum(1 for t in self.turns if t.failed)

    def transcript(self) -> str:
        """The conversation as plain text, for export and for the model's context."""
        lines = []
        for turn in self.turns:
            if turn.failed:
                continue
            who = "User" if turn.speaker is Speaker.PARTICIPANT else "Assistant"
            lines.append(f"{who}: {turn.text}")
        return "\n\n".join(lines)


class ConversationClosed(RuntimeError):
    """The intervention period is over; nothing further may be recorded."""
