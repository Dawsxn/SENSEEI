"""The closed sets of values the schema stores.

Stored as text, not as native Postgres enum types: adding a value to a native
enum needs its own migration, and `status` will gain values.

The SEE-I step values are capitalised because that is exactly how they appear in
the rubric YAML and in the eval dataset. The agents are handed this string, so a
mismatch here would silently break rubric lookup.
"""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    #: Trial mode only: scores the pre-tests and post-tests and sees nothing else.
    GRADER = "grader"


class SeeiStep(str, Enum):
    STATE = "State"
    ELABORATE = "Elaborate"
    EXEMPLIFY = "Exemplify"
    ILLUSTRATE = "Illustrate"


class SessionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FALLBACK = "fallback"
    #: Trial mode only: the participant's session time ran out mid-session.
    TIMED_OUT = "timed_out"
    #: The student left with the session's exit and confirmed it. Kept rather
    #: than deleted, so how often students quit partway, and where, can be read
    #: back. Never counted, and never shown to the student again.
    LEFT = "left"
    #: Never finished and never left: the tab was closed, or the phone dropped
    #: the page. Marked when the same student next starts the same reading, the
    #: first moment it is certain the session is dead. Never counted either.
    ABANDONED = "abandoned"


#: The statuses of a session that has ended, which is what every count and
#: statistic is over. A session cut off by the trial's clock ended too, and is
#: counted like the others: the trial's analysis is intention-to-treat.
FINISHED_STATUSES: tuple[str, ...] = (
    SessionStatus.COMPLETE.value,
    SessionStatus.FALLBACK.value,
    SessionStatus.TIMED_OUT.value,
)


class ClassMode(str, Enum):
    """What a class's students do with a reading.

    Ordinary classes are all SEE-I. The other two exist only in trial mode, for
    the study's control groups (docs/context/trial.md).
    """

    SEEI = "seei"
    CHATBOT = "chatbot"
    READING_ONLY = "reading_only"


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


#: Advancement order. The Orchestrator walks this; nothing else defines it.
STEP_ORDER: tuple[SeeiStep, ...] = (
    SeeiStep.STATE,
    SeeiStep.ELABORATE,
    SeeiStep.EXEMPLIFY,
    SeeiStep.ILLUSTRATE,
)
