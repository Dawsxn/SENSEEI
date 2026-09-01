"""Where the trial's participants actually live, so a restart does not lose them.

Until this existed, participants were held in memory. In a single-sitting trial
that is a hazard with no recovery: a process restart forty minutes into the
session loses forty-five people, and the afternoon cannot be run again. Whatever
else is unfinished, this is the piece that separates a rehearsal from something
that can collect real data.

**Two tables, and the split between them is not incidental.** Section 4.7.4
requires that "data containing participant identifiers will be handled separately
from research data". So identities live in one table, keyed by participant id and
holding nothing else; everything a participant produced lives in the other,
keyed by that id and holding no name. The pseudonymisation of Section 4.6.6 is
then a property of the schema rather than a discipline someone has to remember
when writing an export.

**A participant is stored as one snapshot, not as a relational spread.** The
alternative — a table per phase visit, per conversational turn, per scroll sample
— would mean a second definition of every domain object, kept in step with the
first by hand. At forty-five participants there is nothing to gain from it: no
query runs against this data during the trial, and the export is generated from
the domain objects either way. What matters is that a restart restores exactly
what was there, and that is easier to guarantee against one serialiser than
against six tables.

The snapshot is rewritten on every change rather than appended to. There is no
history of a participant's record, only its current truth, which is what the
analysis reads.

**SQLite locally, PostgreSQL in the lab.** The URL decides, and both work. Do not
run a real sitting on SQLite from a container filesystem: on Render or Railway
that file does not survive a redeploy, which would reintroduce the exact failure
this module exists to remove.
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    String,
    Text,
    create_engine,
    delete,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Session

#: Local default. Fine for development and for tests; see the note above about
#: never running a real sitting on an ephemeral filesystem.
DEFAULT_URL = "sqlite:///study-trial.db"


class Base(DeclarativeBase):
    pass


class ParticipantRow(Base):
    """One participant's research data. Carries no identity."""

    __tablename__ = "participant"

    participant_id = Column(String(32), primary_key=True)
    trial_id = Column(String(64), nullable=False, default="")
    arm = Column(String(32), nullable=False)
    access_code = Column(String(64), nullable=False, unique=True, index=True)
    checked_in_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    snapshot = Column(Text, nullable=False)


class IdentityRow(Base):
    """A participant's identity, held apart from their research data (§4.7.4).

    Deliberately its own table rather than columns on ``participant``. It is what
    lets a withdrawal be honoured — the link back to the person has to exist to
    find their record — while keeping the name out of everything the analysis
    touches.
    """

    __tablename__ = "participant_identity"

    participant_id = Column(String(32), primary_key=True)
    name = Column(String(200), nullable=False, default="")
    consent_form_serial = Column(String(64), nullable=False, default="")
    recorded_at = Column(DateTime(timezone=True))


class Repository:
    """Reads and writes participants. The only thing that touches the database."""

    def __init__(self, url: str = DEFAULT_URL, echo: bool = False):
        self.url = url
        self.engine = create_engine(url, echo=echo, future=True)
        Base.metadata.create_all(self.engine)

    # --- writing ----------------------------------------------------------

    def save(self, participant, trial_id: str = "") -> None:
        """Write a participant's current state, replacing what was there.

        Called after every change rather than at the end of a session. A crash
        is not announced in advance, so anything not yet written is lost, and the
        cost of writing a few kilobytes per interaction is nothing next to
        re-running a lab booking.
        """
        now = datetime.now(participant.checked_in_at.tzinfo) if participant.checked_in_at else None

        with Session(self.engine) as session:
            row = session.get(ParticipantRow, participant.participant_id)
            if row is None:
                row = ParticipantRow(participant_id=participant.participant_id)
                session.add(row)

            row.trial_id = trial_id
            row.arm = participant.arm.value
            row.access_code = participant.access_code
            row.checked_in_at = participant.checked_in_at
            row.updated_at = now
            row.snapshot = json.dumps(snapshot_of(participant))

            identity = session.get(IdentityRow, participant.participant_id)
            if identity is None:
                identity = IdentityRow(participant_id=participant.participant_id)
                session.add(identity)
            identity.name = participant.name or ""
            identity.consent_form_serial = participant.consent_form_serial or ""
            identity.recorded_at = participant.checked_in_at

            session.commit()

    # --- reading ----------------------------------------------------------

    def load_all(self, restore) -> list:
        """Every stored participant, oldest first.

        ``restore`` turns a snapshot dict back into a participant; it lives in
        the store rather than here because rebuilding an unguided session needs
        the chat backend, which is not this module's business.
        """
        with Session(self.engine) as session:
            rows = session.scalars(
                select(ParticipantRow).order_by(ParticipantRow.participant_id)
            ).all()
            identities = {
                row.participant_id: row
                for row in session.scalars(select(IdentityRow)).all()
            }

            participants = []
            for row in rows:
                identity = identities.get(row.participant_id)
                participants.append(
                    restore(
                        json.loads(row.snapshot),
                        name=identity.name if identity else "",
                        consent_form_serial=(
                            identity.consent_form_serial if identity else ""
                        ),
                    )
                )
            return participants

    def count(self) -> int:
        with Session(self.engine) as session:
            return len(session.scalars(select(ParticipantRow.participant_id)).all())

    # --- deletion ---------------------------------------------------------

    def delete(self, participant_id: str) -> bool:
        """Erase a participant entirely, identity included (§4.7.1, §4.6.6).

        Both tables, in one transaction. Removing the research data while leaving
        the identity behind, or the reverse, would leave a withdrawn participant
        half-present in the study — which is not what withdrawing means.
        """
        with Session(self.engine) as session:
            row = session.get(ParticipantRow, participant_id)
            session.execute(
                delete(IdentityRow).where(IdentityRow.participant_id == participant_id)
            )
            if row is not None:
                session.delete(row)
            session.commit()
            return row is not None

    def delete_everything(self) -> None:
        """Drop all study data, for the end of the retention period (§4.6.6)."""
        with Session(self.engine) as session:
            session.execute(delete(IdentityRow))
            session.execute(delete(ParticipantRow))
            session.commit()


def snapshot_of(participant) -> dict:
    """One participant's research data as a plain dict.

    Identity is deliberately absent: it belongs in the other table, and putting
    it here would put a name inside the record the analysis reads.
    """
    from .phases import state_to_dict

    return {
        "participant_id": participant.participant_id,
        "arm": participant.arm.value,
        "access_code": participant.access_code,
        "checked_in_at": (
            participant.checked_in_at.isoformat()
            if participant.checked_in_at
            else None
        ),
        "state": state_to_dict(participant.state),
        "unguided": (
            participant.unguided.snapshot() if participant.unguided else None
        ),
        "passive": participant.passive.snapshot() if participant.passive else None,
        "responses": {
            phase.value: result.snapshot()
            for phase, result in participant.responses.items()
        },
        "incidents": list(participant.incidents),
        "unavailable": participant.unavailable,
    }
