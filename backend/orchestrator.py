"""The Orchestrator: the fixed rules of the tutoring loop.

This is the plain backend logic the architecture keeps out of the two agents:
pass/fail, retries, and step advancement. It calls no LLM and touches no
database. Given where a session is and how the latest attempt was graded, it
returns what should happen next. The service layer carries that decision out
(persisting rows, calling the agents); this module only decides.

Keeping it pure is the point. Every branch below is a unit test with plain
values, no Postgres and no mocking, which is exactly what could not be done
while these rules lived inline in scripts/session.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from agents.tutor import FINAL_FAIL, FIRST_ATTEMPT, PASSED, RETRY

from .models import STEP_ORDER, SeeiStep, SessionStatus, Verdict

#: Attempts a student gets per SEE-I step before the step ends in fallback. This
#: is the single home for the number: scripts/session.py and scripts/seed.py
#: both import it from here rather than keeping their own copy, so the loop and
#: the seeded data can never disagree about it.
MAX_ATTEMPTS = 3


def next_step(step: SeeiStep) -> SeeiStep | None:
    """The step after this one, or None if this is the last (Illustrate)."""
    i = STEP_ORDER.index(step)
    return STEP_ORDER[i + 1] if i + 1 < len(STEP_ORDER) else None


def attempts_left(attempt_number: int) -> int:
    """How many attempts remain after the given (1-based) attempt."""
    return max(MAX_ATTEMPTS - attempt_number, 0)


@dataclass(frozen=True)
class Decision:
    """What happens after one graded attempt.

    - `situation` is the tutor situation for the reply to this attempt.
    - `new_status` / `new_current_step` are where the session sits afterwards.
    - `open_next`, when set, is the step whose opening Prompt should follow the
      reply. It is set only when a pass advances to a new step, because that is
      the only time a fresh FIRST_ATTEMPT question is owed.
    - `fallback` asks for the static "contact your instructor" copy after the
      reply. It is not written by the Tutor (see agent-contracts.md).
    """

    situation: str
    new_status: SessionStatus
    new_current_step: SeeiStep
    open_next: SeeiStep | None = None
    fallback: bool = False

    @property
    def terminal(self) -> bool:
        return self.new_status in (SessionStatus.COMPLETE, SessionStatus.FALLBACK)


#: The dialogue moves each situation composes. The Orchestrator records these
#: rather than asking the agent which it used: it chose the situation, so it
#: already knows. Stored on each tutor_message for later behaviour checks.
MOVES: dict[str, list[str]] = {
    FIRST_ATTEMPT: ["Prompt"],
    RETRY: ["Acknowledgement", "Criterion-Based Feedback", "Re-Prompt"],
    FINAL_FAIL: ["Acknowledgement", "Criterion-Based Feedback"],
    PASSED: ["Acknowledgement", "Transition"],
}


def opening_situation() -> str:
    """The situation for the very first message of any step: the Prompt."""
    return FIRST_ATTEMPT


def resolve(step: SeeiStep, attempt_number: int, verdict: Verdict) -> Decision:
    """Decide what follows an attempt graded `verdict` on `step`.

    `attempt_number` is 1-based: the first response to a step is attempt 1.
    """
    if verdict is Verdict.PASS:
        nxt = next_step(step)
        if nxt is None:
            # Passed the last step: the session is done.
            return Decision(PASSED, SessionStatus.COMPLETE, step)
        # Passed, more steps remain: acknowledge, then open the next step.
        return Decision(PASSED, SessionStatus.IN_PROGRESS, nxt, open_next=nxt)

    # FAIL.
    if attempt_number < MAX_ATTEMPTS:
        # Attempts remain: feedback and ask again, same step.
        return Decision(RETRY, SessionStatus.IN_PROGRESS, step)

    # No attempts left: feedback with no re-prompt, then fallback ends the session.
    return Decision(FINAL_FAIL, SessionStatus.FALLBACK, step, fallback=True)


#: The static message shown when a step exhausts its attempts. Deliberately not
#: written by the Tutor: it is the same sentence every time, and generating it
#: invites the model to soften it or add a hint the student cannot act on.
FALLBACK_MESSAGE = (
    "You have used all your attempts for this step. Your instructor has been "
    "notified and can go through it with you."
)
