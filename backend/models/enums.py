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


class SeeiStep(str, Enum):
    STATE = "State"
    ELABORATE = "Elaborate"
    EXEMPLIFY = "Exemplify"
    ILLUSTRATE = "Illustrate"


class SessionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FALLBACK = "fallback"


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
