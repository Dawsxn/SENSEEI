"""Trial mode: participant IDs, signing in with one, and the clock.

Everything here is refused unless `TRIAL_MODE` is on (docs/context/trial.md).

A participant is an ordinary student underneath: a user row enrolled in the
class for their group. That keeps the tutoring loop, the roster and the
statistics on one path. This module adds what makes them a participant:

- **IDs in batches.** The research team makes one batch per sitting, choosing
  how many IDs each class gets. The IDs are drawn in a shuffled order, which is
  the order the slips print in, so a stack of slips shows nothing about groups.
- **Sign-in by ID alone.** It works while the ID is not voided and its batch is
  open. Closing the batch signs everyone in it out.
- **The clock.** It starts when the participant's reading first opens and runs
  for `TRIAL_MINUTES`. A session still going when it runs out is ended as
  `timed_out` and kept, like any other ended session.
- **One session per participant**, checked when one is started.
- **Done**, for the two control groups, who have no session to finish.
- **The event log**: what a participant did, for the analysis. Their browser
  sends what it sees (panels, pages, pastes, the tab); the server records what
  only it knows (the reading opening, Done, a failed AI turn).

The server holds the clock. The countdown on screen is only a display of it, so
nothing the browser sends can buy more time.
"""

from __future__ import annotations

import random
import re
import secrets
import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    FINISHED_STATUSES,
    ChatMessage,
    Class,
    ClassMode,
    Enrolment,
    Participant,
    ParticipantBatch,
    Reading,
    ReadingAssignment,
    Role,
    Session,
    SessionStatus,
    TrialEvent,
    User,
    class_label,
    utcnow,
)
from ..settings import get_settings
from .class_service import CODE_ALPHABET, CODE_HALF

#: Most IDs one batch may hold. Far above a sitting, low enough that a typo in a
#: count cannot fill the database.
MAX_BATCH = 300

#: What a participant's browser may report. Each has a stated purpose in
#: docs/context/trial.md; anything else is refused rather than stored.
CLIENT_EVENTS = frozenset(
    {
        "panel_opened",      # data: {"panel": "rubric" | "components"}
        "panel_closed",      # data: {"panel": ...}
        "page_changed",      # data: {"page": n}
        "reply_shown",       # a tutor or chatbot reply finished streaming
        "first_keystroke",   # the first key typed after a reply
        "paste",             # data: {"length": n}. Never the pasted text
        "tab_left",
        "tab_returned",
    }
)
#: What the server records itself, because only it knows.
SERVER_EVENTS = frozenset({"reading_opened", "done", "turn_failed"})

#: A browser clock this far from the server's is not believed; the event is
#: stamped with the server's time instead.
CLOCK_TRUST = timedelta(hours=1)


class TrialOff(Exception):
    """Trial mode is not on, so none of this exists."""


class UnknownParticipant(Exception):
    """No participant has this ID."""


class InactiveParticipant(Exception):
    """The ID was voided, or its batch is closed."""


class BatchNotFound(Exception):
    """No such batch, or not this instructor's."""


class InvalidBatch(Exception):
    """The requested batch cannot be made; the message says why."""


class NotDoneable(Exception):
    """Done does not apply: a SEE-I participant, or one whose reading never opened."""


def require_trial() -> None:
    if not get_settings().trial_mode:
        raise TrialOff


# --------------------------------------------------------------------------- #
# IDs


def new_code() -> str:
    """`P-7K3Q-9TXM`: the join code's alphabet, with a prefix that says what it is."""
    chars = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_HALF * 2))
    return f"P-{chars[:CODE_HALF]}-{chars[CODE_HALF:]}"


def normalize_code(raw: str) -> str:
    """Accept an ID the way people type it: any case, spaces, missing hyphens,
    with or without the `P`."""
    cleaned = re.sub(r"[^0-9A-Za-z]", "", raw).upper()
    if len(cleaned) == CODE_HALF * 2 + 1 and cleaned.startswith("P"):
        cleaned = cleaned[1:]
    if len(cleaned) == CODE_HALF * 2:
        return f"P-{cleaned[:CODE_HALF]}-{cleaned[CODE_HALF:]}"
    return raw.strip().upper()


async def _fresh_codes(db: AsyncSession, n: int) -> list[str]:
    """`n` IDs that no participant holds, drawn again on the rare collision."""
    codes: set[str] = set()
    while len(codes) < n:
        wanted = {new_code() for _ in range(n - len(codes))}
        taken = set(
            await db.scalars(
                select(Participant.code).where(Participant.code.in_(list(wanted)))
            )
        )
        codes |= wanted - taken
    return list(codes)


# --------------------------------------------------------------------------- #
# a participant, from their own side


async def participant_for(db: AsyncSession, user_id: uuid.UUID) -> Participant | None:
    return await db.scalar(select(Participant).where(Participant.user_id == user_id))


async def is_active(db: AsyncSession, participant: Participant) -> bool:
    if participant.voided_at is not None:
        return False
    closed = await db.scalar(
        select(ParticipantBatch.closed_at).where(ParticipantBatch.id == participant.batch_id)
    )
    return closed is None


async def sign_in(db: AsyncSession, raw_code: str) -> User:
    """The user an ID signs in as. The first sign-in is recorded."""
    require_trial()
    participant = await db.scalar(
        select(Participant).where(Participant.code == normalize_code(raw_code))
    )
    if participant is None:
        raise UnknownParticipant
    if not await is_active(db, participant):
        raise InactiveParticipant
    if participant.signed_in_at is None:
        participant.signed_in_at = utcnow()
        await db.commit()
    user = await db.scalar(select(User).where(User.id == participant.user_id))
    assert user is not None  # the foreign key cascades
    return user


def deadline(participant: Participant) -> datetime | None:
    if participant.clock_started_at is None:
        return None
    return participant.clock_started_at + timedelta(minutes=get_settings().trial_minutes)


async def expire_if_due(
    db: AsyncSession, participant: Participant, now: datetime | None = None
) -> bool:
    """End a session the clock has run out on. True once time is up.

    The session ends at the deadline, not whenever this happens to run, so its
    length reads the same however late the participant's next request comes.
    """
    end = deadline(participant)
    now = now or utcnow()
    if end is None or now < end:
        return False
    await db.execute(
        update(Session)
        .where(
            Session.student_id == participant.user_id,
            Session.status == SessionStatus.IN_PROGRESS.value,
        )
        .values(status=SessionStatus.TIMED_OUT.value, ended_at=end)
    )
    await db.commit()
    return True


async def _their_reading(db: AsyncSession, class_id: uuid.UUID) -> uuid.UUID | None:
    """The reading a participant works on: their class's, the first if several."""
    return await db.scalar(
        select(Reading.id)
        .join(ReadingAssignment, ReadingAssignment.reading_id == Reading.id)
        .where(
            ReadingAssignment.class_id == class_id,
            ReadingAssignment.deleted_at.is_(None),
            Reading.deleted_at.is_(None),
        )
        .order_by(Reading.created_at)
        .limit(1)
    )


async def status(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Where a participant is: their mode, their reading, their time, their
    session. Ending a session whose time is up happens here too, so asking is
    enough to make the record right."""
    require_trial()
    participant = await participant_for(db, user_id)
    if participant is None:
        raise UnknownParticipant
    time_up = await expire_if_due(db, participant)
    mode = await db.scalar(select(Class.mode).where(Class.id == participant.class_id))
    sess = await db.scalar(
        select(Session)
        .where(Session.student_id == user_id)
        .order_by(Session.started_at.desc())
        .limit(1)
    )
    end = deadline(participant)
    return {
        "code": participant.code,
        "done": participant.done_at is not None,
        "mode": ClassMode(mode).value,
        "reading_id": await _their_reading(db, participant.class_id),
        "minutes": get_settings().trial_minutes,
        "seconds_left": (
            None if end is None else max(int((end - utcnow()).total_seconds()), 0)
        ),
        "time_up": time_up,
        "session": (
            None if sess is None
            else {"id": sess.id, "status": SessionStatus(sess.status).value}
        ),
    }


async def start_clock(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Start the participant's time, once. Later calls change nothing."""
    require_trial()
    participant = await participant_for(db, user_id)
    if participant is None:
        raise UnknownParticipant
    if participant.clock_started_at is None:
        participant.clock_started_at = utcnow()
        db.add(_event(participant, "reading_opened", at=participant.clock_started_at))
        await db.commit()
    return await status(db, user_id)


async def finish(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Done, for the chatbot and reading-only groups. Once, and only in time."""
    require_trial()
    participant = await participant_for(db, user_id)
    if participant is None:
        raise UnknownParticipant
    mode = await db.scalar(select(Class.mode).where(Class.id == participant.class_id))
    if ClassMode(mode) is ClassMode.SEEI:
        raise NotDoneable("a SEE-I session ends by itself")
    if participant.clock_started_at is None:
        raise NotDoneable("the reading has not opened")
    if participant.done_at is None and not await expire_if_due(db, participant):
        participant.done_at = utcnow()
        db.add(_event(participant, "done", at=participant.done_at))
        await db.commit()
    return await status(db, user_id)


# --------------------------------------------------------------------------- #
# the event log


def _event(
    participant: Participant, kind: str, data: dict | None = None, at: datetime | None = None
) -> TrialEvent:
    return TrialEvent(participant_id=participant.id, kind=kind, data=data, at=at or utcnow())


async def record(
    db: AsyncSession, user_id: uuid.UUID, events: list[tuple[str, datetime, dict | None]]
) -> int:
    """Store what a participant's browser reports. Unknown kinds are dropped,
    and a time the browser's clock got badly wrong is replaced by the server's.
    Returns how many were kept."""
    require_trial()
    participant = await participant_for(db, user_id)
    if participant is None:
        raise UnknownParticipant
    now = utcnow()
    kept = 0
    for kind, at, data in events:
        if kind not in CLIENT_EVENTS:
            continue
        if at.tzinfo is None or abs(at - now) > CLOCK_TRUST:
            at = now
        db.add(_event(participant, kind, data or None, at))
        kept += 1
    await db.commit()
    return kept


async def note(db: AsyncSession, user_id: uuid.UUID, kind: str, data: dict | None = None) -> None:
    """Record a server-side event for a participant. Does nothing for anyone
    else, or outside trial mode, so the shared code paths can call it freely."""
    assert kind in SERVER_EVENTS
    if not get_settings().trial_mode:
        return
    participant = await participant_for(db, user_id)
    if participant is None:
        return
    db.add(_event(participant, kind, data))
    await db.commit()


# --------------------------------------------------------------------------- #
# the chatbot group


async def refuse_chat(db: AsyncSession, user_id: uuid.UUID) -> str | None:
    """Why this participant may not send a chatbot message, or None."""
    if not get_settings().trial_mode:
        return "not found"
    participant = await participant_for(db, user_id)
    if participant is None:
        return "not found"
    mode = await db.scalar(select(Class.mode).where(Class.id == participant.class_id))
    if ClassMode(mode) is not ClassMode.CHATBOT:
        return "this class does not use the chatbot"
    if participant.clock_started_at is None:
        return "the reading has not opened"
    if await expire_if_due(db, participant):
        return "time is up"
    if participant.done_at is not None:
        return "you are done"
    return None


async def chat_history(db: AsyncSession, user_id: uuid.UUID) -> list[ChatMessage]:
    require_trial()
    participant = await participant_for(db, user_id)
    if participant is None:
        raise UnknownParticipant
    rows = await db.scalars(
        select(ChatMessage)
        .where(ChatMessage.participant_id == participant.id)
        .order_by(ChatMessage.created_at)
    )
    return list(rows)


async def refuse_start(db: AsyncSession, user_id: uuid.UUID) -> str | None:
    """Why this user may not start a session, or None if they may.

    Only participants are limited. Their clock starts here if the reading step
    somehow never started it, so no session runs without a deadline.
    """
    if not get_settings().trial_mode:
        return None
    participant = await participant_for(db, user_id)
    if participant is None:
        return None
    mode = await db.scalar(select(Class.mode).where(Class.id == participant.class_id))
    if ClassMode(mode) is not ClassMode.SEEI:
        return "this class does not use SEE-I"
    if participant.clock_started_at is None:
        participant.clock_started_at = utcnow()
        await db.commit()
    if await expire_if_due(db, participant):
        return "time is up"
    started = await db.scalar(
        select(func.count()).select_from(Session).where(Session.student_id == user_id)
    )
    if started:
        return "you have already had your session"
    return None


async def out_of_time(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """Whether a participant's time is up, ending their session if so."""
    if not get_settings().trial_mode:
        return False
    participant = await participant_for(db, user_id)
    return participant is not None and await expire_if_due(db, participant)


# --------------------------------------------------------------------------- #
# the research team's side


def _participant_status(p: Participant, finished: bool) -> str:
    if p.voided_at is not None:
        return "voided"
    if finished:
        return "finished"
    if p.signed_in_at is not None:
        return "signed_in"
    return "not_used"


async def _owned_batch(
    db: AsyncSession, instructor_id: uuid.UUID, batch_id: uuid.UUID
) -> ParticipantBatch:
    batch = await db.scalar(
        select(ParticipantBatch).where(
            ParticipantBatch.id == batch_id,
            ParticipantBatch.instructor_id == instructor_id,
        )
    )
    if batch is None:
        raise BatchNotFound
    return batch


async def list_batches(db: AsyncSession, instructor_id: uuid.UUID) -> list[dict]:
    require_trial()
    total = (
        select(func.count())
        .select_from(Participant)
        .where(Participant.batch_id == ParticipantBatch.id)
        .scalar_subquery()
    )
    used = (
        select(func.count())
        .select_from(Participant)
        .where(
            Participant.batch_id == ParticipantBatch.id,
            Participant.signed_in_at.is_not(None),
        )
        .scalar_subquery()
    )
    rows = await db.execute(
        select(ParticipantBatch, total, used)
        .where(ParticipantBatch.instructor_id == instructor_id)
        .order_by(ParticipantBatch.created_at.desc())
    )
    return [
        {
            "id": b.id,
            "name": b.name,
            "created_at": b.created_at,
            "closed_at": b.closed_at,
            "id_count": n_total,
            "used_count": n_used,
        }
        for b, n_total, n_used in rows
    ]


async def get_batch(
    db: AsyncSession, instructor_id: uuid.UUID, batch_id: uuid.UUID
) -> dict:
    require_trial()
    batch = await _owned_batch(db, instructor_id, batch_id)
    rows = (
        await db.execute(
            select(Participant, class_label(), Class.mode)
            .join(Class, Class.id == Participant.class_id)
            .where(Participant.batch_id == batch_id)
            .order_by(Participant.position)
        )
    ).all()
    finished = set(
        await db.scalars(
            select(Session.student_id).where(
                Session.student_id.in_([p.user_id for p, _, _ in rows]),
                Session.status.in_(FINISHED_STATUSES),
            )
        )
    )
    # The control groups have no session: pressing Done, or running out of
    # time, is how they finish.
    now = utcnow()
    for p, _, _ in rows:
        end = deadline(p)
        if p.done_at is not None or (end is not None and now >= end):
            finished.add(p.user_id)
    return {
        "id": batch.id,
        "name": batch.name,
        "created_at": batch.created_at,
        "closed_at": batch.closed_at,
        "participants": [
            {
                "id": p.id,
                "code": p.code,
                "class_id": p.class_id,
                "class_label": label,
                "mode": ClassMode(mode).value,
                "status": _participant_status(p, p.user_id in finished),
            }
            for p, label, mode in rows
        ],
    }


async def create_batch(
    db: AsyncSession,
    instructor_id: uuid.UUID,
    name: str,
    counts: dict[uuid.UUID, int],
) -> dict:
    """Make a batch: `counts[class_id]` IDs for each class, in a shuffled order.

    Each ID gets its own student, enrolled in its class. The student's name is
    the ID and their email is empty: nothing in the app says who they are.
    """
    require_trial()
    counts = {class_id: n for class_id, n in counts.items() if n > 0}
    total = sum(counts.values())
    if total == 0:
        raise InvalidBatch("a batch needs at least one ID")
    if total > MAX_BATCH:
        raise InvalidBatch(f"a batch holds at most {MAX_BATCH} IDs")

    owned = set(
        await db.scalars(
            select(Class.id).where(
                Class.id.in_(list(counts)),
                Class.instructor_id == instructor_id,
                Class.deleted_at.is_(None),
            )
        )
    )
    if owned != set(counts):
        raise InvalidBatch("one of those classes does not exist")

    order = [class_id for class_id, n in counts.items() for _ in range(n)]
    random.SystemRandom().shuffle(order)
    codes = await _fresh_codes(db, total)

    batch = ParticipantBatch(instructor_id=instructor_id, name=name)
    db.add(batch)
    await db.flush()
    for position, (class_id, code) in enumerate(zip(order, codes)):
        user = User(
            role=Role.STUDENT,
            name=code,
            email="",
            google_sub=f"participant:{code}",
            participant_identifier=code,
        )
        db.add(user)
        await db.flush()
        db.add(Enrolment(student_id=user.id, class_id=class_id))
        db.add(
            Participant(
                batch_id=batch.id,
                user_id=user.id,
                class_id=class_id,
                code=code,
                position=position,
            )
        )
    await db.commit()
    return await get_batch(db, instructor_id, batch.id)


async def close_batch(
    db: AsyncSession, instructor_id: uuid.UUID, batch_id: uuid.UUID
) -> dict:
    """End the sitting: the IDs stop working, and any session still going ends.

    A session still running when its batch closes is cut off the same way the
    clock would cut it off, so it is recorded the same way.
    """
    require_trial()
    batch = await _owned_batch(db, instructor_id, batch_id)
    if batch.closed_at is None:
        now = utcnow()
        batch.closed_at = now
        users = select(Participant.user_id).where(Participant.batch_id == batch_id)
        await db.execute(
            update(Session)
            .where(
                Session.student_id.in_(users),
                Session.status == SessionStatus.IN_PROGRESS.value,
            )
            .values(status=SessionStatus.TIMED_OUT.value, ended_at=now)
        )
        await db.commit()
    return await get_batch(db, instructor_id, batch_id)


async def void_participant(
    db: AsyncSession,
    instructor_id: uuid.UUID,
    batch_id: uuid.UUID,
    participant_id: uuid.UUID,
) -> dict:
    """Stop one ID working: a spoiled slip, or someone who left."""
    require_trial()
    await _owned_batch(db, instructor_id, batch_id)
    participant = await db.scalar(
        select(Participant).where(
            Participant.id == participant_id, Participant.batch_id == batch_id
        )
    )
    if participant is None:
        raise BatchNotFound
    if participant.voided_at is None:
        participant.voided_at = utcnow()
        await db.commit()
    return await get_batch(db, instructor_id, batch_id)
