"""Where a running trial keeps its participants. In memory, for now.

Deliberately not a database yet. The persistence layer is a later step, and
wiring one in before the flow is settled would mean migrating a schema that is
still moving. Everything here is behind :class:`TrialStore`, so swapping in
Postgres is one class rather than a rewrite.

**This must not run a real session.** A process restart loses every participant,
which during collection would mean 45 people with no data and no way to redo the
sitting. :meth:`TrialStore.is_durable` reports False, and the pre-flight refuses
a live run against it.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime

from ..arms import Arm
from ..interventions.passive import PassiveSession
from ..interventions.unguided import ChatBackend, UnguidedSession
from ..phases import ParticipantState, Phase, start


@dataclass
class Participant:
    """One person in the trial, and everything their session produced."""

    participant_id: str
    arm: Arm
    state: ParticipantState

    #: The code they type to get back in after a browser crash. Random rather
    #: than sequential so one participant cannot open another's session.
    access_code: str

    #: Their identity, held here only so consent can be verified and a
    #: withdrawal can find their record (§4.6.6). Never exported: the export
    #: keys on participant_id alone.
    name: str = ""
    consent_form_serial: str = ""

    checked_in_at: datetime | None = None

    #: Whichever intervention their arm calls for. The SENSEE-I arm has neither,
    #: because its session lives in the application.
    unguided: UnguidedSession | None = None
    passive: PassiveSession | None = None

    #: Instrument results, keyed by phase.
    responses: dict[Phase, object] = field(default_factory=dict)

    #: Anything the proctor logged against this participant during the run.
    incidents: list[str] = field(default_factory=list)

    #: Set when their arm's tool could not be started at all. A technical
    #: failure, not a measurement — kept distinct from low engagement.
    unavailable: str = ""

    @property
    def display_name(self) -> str:
        return self.name or self.participant_id

    def record(self, phase: Phase, result) -> None:
        """Store an instrument result, replacing any earlier attempt at it.

        An incomplete submission is kept rather than discarded, so a participant
        bounced back by a missed required item sees their answers again instead
        of retyping them.
        """
        self.responses[phase] = result

    def draft_answers(self, phase: Phase) -> dict:
        result = self.responses.get(phase)
        return dict(getattr(result, "answers", {}) or {})

    def missing_answers(self, phase: Phase) -> tuple:
        result = self.responses.get(phase)
        return tuple(getattr(result, "missing", ()) or ())

    def attention_totals(self) -> tuple[int, int]:
        """Attention checks failed and answered, across every instrument (§4.6.3)."""
        failed = sum(
            getattr(r, "attention_failed", 0) for r in self.responses.values()
        )
        answered = sum(
            getattr(r, "attention_answered", 0) for r in self.responses.values()
        )
        return failed, answered

    @property
    def sus_score(self) -> float | None:
        """The SUS composite, once answered. SENSEE-I arm only (§4.6.5)."""
        for result in self.responses.values():
            value = getattr(result, "sus_score", None)
            if value is not None:
                return value
        return None


class TrialStore:
    """The participants of one trial run."""

    #: In-memory only: a restart loses everything. See the module docstring.
    is_durable = False

    def __init__(self, config, chat_backend: ChatBackend | None = None):
        self.config = config
        self.chat_backend = chat_backend
        self.allocation = config.allocation()
        self._participants: dict[str, Participant] = {}
        self._by_code: dict[str, str] = {}

    # --- check-in ---------------------------------------------------------

    def check_in(
        self,
        now: datetime,
        name: str = "",
        consent_form_serial: str = "",
    ) -> Participant:
        """Register the next participant and assign their arm.

        The arm comes from the next slot in the pre-generated allocation
        sequence, so assignment is neither chosen here nor re-drawn — it was
        fixed before anyone walked in.
        """
        position = len(self._participants)
        arm = self.allocation.arm_for(position)
        participant_id = f"P-{position + 1:03d}"

        participant = Participant(
            participant_id=participant_id,
            arm=arm,
            state=start(participant_id, arm, now),
            access_code=secrets.token_urlsafe(6),
            name=name,
            consent_form_serial=consent_form_serial,
            checked_in_at=now,
        )

        self._participants[participant_id] = participant
        self._by_code[participant.access_code] = participant_id
        return participant

    # --- lookup -----------------------------------------------------------

    def get(self, participant_id: str) -> Participant | None:
        return self._participants.get(participant_id)

    def by_code(self, access_code: str) -> Participant | None:
        participant_id = self._by_code.get(access_code)
        return self._participants.get(participant_id) if participant_id else None

    def all(self) -> list[Participant]:
        return list(self._participants.values())

    @property
    def checked_in(self) -> int:
        return len(self._participants)

    @property
    def remaining_slots(self) -> int:
        return len(self.allocation) - self.checked_in

    def counts_by_arm(self) -> dict[Arm, int]:
        counts = {arm: 0 for arm in Arm}
        for participant in self._participants.values():
            counts[participant.arm] += 1
        return counts

    # --- the intervention -------------------------------------------------

    def begin_intervention(self, participant: Participant, now: datetime) -> None:
        """Open whichever intervention this participant's arm calls for.

        The SENSEE-I arm gets nothing here: its session runs in the application,
        and the harness only links to it and reads telemetry back afterwards.
        """
        if participant.arm is Arm.UNGUIDED_LLM and participant.unguided is None:
            if self.chat_backend is None:
                # Record it rather than raise. Raising here left the participant
                # advanced into an intervention with no session behind it, which
                # then read on the console as zero engagement — a broken tool
                # wearing the costume of a disengaged participant, which is the
                # one confusion this console exists to prevent.
                participant.unavailable = (
                    "The assistant is not configured on this server."
                )
                return
            participant.unguided = UnguidedSession(
                participant.participant_id, self.chat_backend, started_at=now
            )
        elif participant.arm is Arm.PASSIVE and participant.passive is None:
            participant.passive = PassiveSession(
                participant.participant_id, started_at=now
            )

    def end_intervention(self, participant: Participant, now: datetime) -> None:
        """Close the intervention record when the period ends."""
        if participant.unguided is not None:
            participant.unguided.close(now)
        if participant.passive is not None:
            participant.passive.close(now)

    # --- withdrawal -------------------------------------------------------

    def withdraw(self, participant_id: str, link=None) -> bool:
        """Delete a participant's record entirely (§4.7.1).

        Removes the harness's own copy and, through the link, whatever the
        application holds. Deleting only one of the two would leave a withdrawn
        participant's transcript sitting in the app.
        """
        participant = self._participants.pop(participant_id, None)
        if participant is None:
            return False
        self._by_code.pop(participant.access_code, None)
        if link is not None:
            link.delete_participant_data(participant_id)
        return True
