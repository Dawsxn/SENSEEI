"""The trial's pre-test and post-test: taking them, and grading them.

A class takes a test when its `test_key` names one (`backend/trial_tests`). A
participant in such a class goes through five stages, and the server, not the
screen, decides which one they are in:

    pretest -> session -> posttest_ready -> posttest -> done

- **pretest**: until the pre-test ends. The reading and the session clock do
  not start before then.
- **session**: the reading, chatbot or SEE-I session, exactly as without tests,
  until it ends: a SEE-I session finishing, Done, or the session time running out.
- **posttest_ready**: the screen that says the post-test is next. Its clock
  starts when they press Start, not when the session ends.
- **posttest**: until it is submitted, its time runs out, or the batch closes.
- **done**.

Each test has its own clock, from when it starts. Answers are saved as they are
typed, so a test that runs out of time keeps everything saved; it simply ends.
A multiple-choice answer, and a true/false set (1 point per statement marked
right), are scored as they are saved. A written answer is scored by the grader,
except one left blank, which scores 0 when its test ends, so the grader is not
asked to grade nothing (they can still change it). A question answered in steps
can lock its first part once a later part has text, so it can't be rewritten
after the rest is seen.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import trial_tests
from ..models import (
    FINISHED_STATUSES,
    Class,
    ClassMode,
    Participant,
    Session,
    TrialAnswer,
    utcnow,
)
from ..settings import get_settings
from ..trial_tests import POST, PRE, WHICH, Item, Test
from . import trial_service

STAGES = ("pretest", "session", "posttest_ready", "posttest", "done")

MAX_TEXT = 5000


class NotOpen(Exception):
    """This test cannot be taken, started or changed right now; the message says why."""


class UnknownItem(Exception):
    """No such question in this test."""


class BadAnswer(Exception):
    """The answer does not fit the question, e.g. a choice that is not an option."""


class BadScore(Exception):
    """A score the question cannot have, or a question not graded by hand."""


class NotGradable(Exception):
    """No such participant to grade, or their test has not ended yet."""


# --------------------------------------------------------------------------- #
# clocks


def minutes(test: Test, which: str) -> int:
    s = get_settings()
    override = s.trial_pretest_minutes if which == PRE else s.trial_posttest_minutes
    return override or (test.pretest_minutes if which == PRE else test.posttest_minutes)


def _prefix(which: str) -> str:
    return "pretest" if which == PRE else "posttest"


def started_at(p: Participant, which: str) -> datetime | None:
    return getattr(p, f"{_prefix(which)}_started_at")


def ended_at(p: Participant, which: str) -> datetime | None:
    return getattr(p, f"{_prefix(which)}_ended_at")


def deadline(p: Participant, test: Test, which: str) -> datetime | None:
    start = started_at(p, which)
    return None if start is None else start + timedelta(minutes=minutes(test, which))


def _end(p: Participant, which: str, at: datetime, by: str) -> None:
    setattr(p, f"{_prefix(which)}_ended_at", at)
    setattr(p, f"{_prefix(which)}_ended_by", by)


async def class_test(db: AsyncSession, class_id: uuid.UUID) -> Test | None:
    key = await db.scalar(select(Class.test_key).where(Class.id == class_id))
    return trial_tests.get(key)


async def _answers(db: AsyncSession, participant_id: uuid.UUID) -> list[TrialAnswer]:
    return list(
        await db.scalars(select(TrialAnswer).where(TrialAnswer.participant_id == participant_id))
    )


async def _zero_blanks(db: AsyncSession, p: Participant, test: Test, which: str, at: datetime) -> None:
    """When a test ends, a scored question with no answer scores 0."""
    have = {(a.test, a.item): a for a in await _answers(db, p.id)}
    for item in test.items(which):
        if not item.scored:
            continue
        row = have.get((which, item.id))
        blank = row is None or not _answered(item, row)
        if not blank or (row is not None and row.score is not None):
            continue
        if row is None:
            row = TrialAnswer(participant_id=p.id, test=which, item=item.id)
            db.add(row)
        row.score, row.scored_at = 0, at


async def end_test(db: AsyncSession, p: Participant, test: Test, which: str, at: datetime, by: str) -> None:
    """End a test that has started and not ended. The caller commits."""
    if started_at(p, which) is None or ended_at(p, which) is not None:
        return
    _end(p, which, at, by)
    await _zero_blanks(db, p, test, which, at)


async def expire(db: AsyncSession, p: Participant, test: Test, now: datetime | None = None) -> None:
    """End any test whose time has run out, at its deadline."""
    now = now or utcnow()
    changed = False
    for which in WHICH:
        end = deadline(p, test, which)
        if end is not None and ended_at(p, which) is None and now >= end:
            await end_test(db, p, test, which, end, "time_up")
            changed = True
    if changed:
        await db.commit()


async def session_over(db: AsyncSession, p: Participant) -> bool:
    """Whether the participant's session (reading, chatbot or SEE-I) has ended."""
    if p.done_at is not None:
        return True
    if await trial_service.expire_if_due(db, p):
        return True
    mode = await db.scalar(select(Class.mode).where(Class.id == p.class_id))
    if ClassMode(mode) is not ClassMode.SEEI:
        return False
    finished = await db.scalar(
        select(Session.id).where(
            Session.student_id == p.user_id, Session.status.in_(FINISHED_STATUSES)
        ).limit(1)
    )
    return finished is not None


async def stage(db: AsyncSession, p: Participant, test: Test | None) -> str | None:
    """Where a participant with tests is. None for a class without them."""
    if test is None:
        return None
    await expire(db, p, test)
    if p.pretest_ended_at is None:
        return "pretest"
    if not await session_over(db, p):
        return "session"
    if p.posttest_started_at is None:
        return "posttest_ready"
    if p.posttest_ended_at is None:
        return "posttest"
    return "done"


async def pretest_pending(db: AsyncSession, p: Participant) -> bool:
    """Whether this participant must finish the pre-test before anything else."""
    test = await class_test(db, p.class_id)
    if test is None:
        return False
    await expire(db, p, test)
    return p.pretest_ended_at is None


async def finished(db: AsyncSession, p: Participant, test: Test | None) -> bool:
    """For the batch page: with tests, finished means the post-test has ended."""
    return test is not None and p.posttest_ended_at is not None


# --------------------------------------------------------------------------- #
# taking a test


async def _mine(db: AsyncSession, user_id: uuid.UUID) -> tuple[Participant, Test]:
    trial_service.require_trial()
    p = await trial_service.participant_for(db, user_id)
    if p is None:
        raise trial_service.UnknownParticipant
    test = await class_test(db, p.class_id)
    if test is None:
        raise NotOpen("this class has no tests")
    return p, test


def _open_stages(which: str) -> tuple[str, ...]:
    return ("pretest",) if which == PRE else ("posttest_ready", "posttest")


def _answered(item: Item, a: TrialAnswer) -> bool:
    if item.kind == "choice":
        return a.choice is not None
    if item.kind == "truefalse":
        return bool(a.parts)
    if item.kind == "steps":
        return any(str(v).strip() for v in (a.parts or {}).values())
    return bool((a.text or "").strip())


def _public_item(item: Item) -> dict:
    """A question as the participant sees it: no answer key, no rubric."""
    return {
        "id": item.id,
        "kind": item.kind,
        "part": item.part,
        "question": item.question,
        "options": [{"key": k, "text": v} for k, v in item.options.items()],
        "statements": [{"key": k, "text": st.text} for k, st in item.statements.items()],
        "steps": [{"key": k, "prompt": v} for k, v in item.steps.items()],
        "lock_first": item.lock_first,
        "points": item.points,
        "ticked": item.ticked,
    }


def _saved(a: TrialAnswer) -> dict:
    return {"item": a.item, "choice": a.choice, "text": a.text, "parts": a.parts, "sure": a.sure}


async def view(db: AsyncSession, user_id: uuid.UUID, which: str) -> dict:
    """The test as its taker sees it, with what they have saved so far."""
    p, test = await _mine(db, user_id)
    where = await stage(db, p, test)
    if where not in _open_stages(which):
        raise NotOpen(f"the {_prefix(which)} is not open")
    end = deadline(p, test, which)
    return {
        "which": which,
        "minutes": minutes(test, which),
        "started": started_at(p, which) is not None,
        "seconds_left": (
            None if end is None else max(int((end - utcnow()).total_seconds()), 0)
        ),
        "part_intros": test.part_intros,
        "items": [_public_item(i) for i in test.items(which)],
        "answers": [_saved(a) for a in await _answers(db, p.id) if a.test == which],
    }


async def start(db: AsyncSession, user_id: uuid.UUID, which: str) -> dict:
    """Start a test's clock, once. Later calls change nothing."""
    p, test = await _mine(db, user_id)
    where = await stage(db, p, test)
    if where not in _open_stages(which):
        raise NotOpen(f"the {_prefix(which)} is not open")
    if started_at(p, which) is None:
        setattr(p, f"{_prefix(which)}_started_at", utcnow())
        await db.commit()
    return await view(db, user_id, which)


def _tf_score(item: Item, marks: dict) -> int:
    """1 point per statement marked right; a blank statement scores 0."""
    return sum(1 for k, st in item.statements.items() if marks.get(k) is st.answer)


def _clean_parts(item: Item, parts: dict, before: dict | None) -> dict:
    """Check an answer in parts against its question, and apply the lock."""
    if not isinstance(parts, dict):
        raise BadAnswer("an answer in parts is a set of named parts")
    if item.kind == "truefalse":
        if set(parts) - set(item.statements) or not all(isinstance(v, bool) for v in parts.values()):
            raise BadAnswer("mark each statement true or false")
        return dict(parts)
    if set(parts) - set(item.steps):
        raise BadAnswer("not one of the question's parts")
    clean = {k: str(v)[:MAX_TEXT] for k, v in parts.items()}
    if item.lock_first and before:
        first, *later = list(item.steps)
        started = any(str(before.get(k) or "").strip() for k in later)
        if started and clean.get(first, before.get(first)) != before.get(first):
            raise BadAnswer(f"part ({first}) can't change once a later part is started")
    return clean


async def save(
    db: AsyncSession,
    user_id: uuid.UUID,
    which: str,
    item_id: str,
    *,
    choice: str | None = None,
    text: str | None = None,
    parts: dict | None = None,
    sure: bool | None = None,
) -> dict:
    """Save one answer as it is typed. Only while the test is running.

    Each save that changes the answer counts as an edit; ticking "sure" does not.
    """
    p, test = await _mine(db, user_id)
    where = await stage(db, p, test)
    running = where == ("pretest" if which == PRE else "posttest") and started_at(p, which)
    if not running:
        raise NotOpen(f"the {_prefix(which)} is not running")
    item = test.item(which, item_id)
    if item is None:
        raise UnknownItem

    row = await db.scalar(
        select(TrialAnswer).where(
            TrialAnswer.participant_id == p.id,
            TrialAnswer.test == which,
            TrialAnswer.item == item_id,
        )
    )
    if row is None:
        row = TrialAnswer(participant_id=p.id, test=which, item=item_id)
        db.add(row)

    before = (row.choice, row.text, row.parts)
    if item.kind == "choice" and choice is not None:
        if choice not in item.options:
            raise BadAnswer("not one of the options")
        row.choice = choice
        row.score = 1 if choice == item.answer else 0
        row.scored_at = utcnow()
    elif item.kind == "text" and text is not None:
        row.text = text[:MAX_TEXT]
    elif item.kind in ("truefalse", "steps") and parts is not None:
        merged = {**(row.parts or {}), **_clean_parts(item, parts, row.parts)}
        row.parts = merged
        if item.kind == "truefalse":
            row.score, row.scored_at = _tf_score(item, merged), utcnow()
    if sure is not None and item.ticked:
        row.sure = sure

    now = utcnow()
    if (row.choice, row.text, row.parts) != before:
        row.edits = (row.edits or 0) + 1
        row.last_changed_at = now
        if row.first_answered_at is None:
            row.first_answered_at = now
    await db.commit()
    return _saved(row)


async def submit(db: AsyncSession, user_id: uuid.UUID, which: str) -> None:
    """End a test by submitting it. Once; submitting an ended test changes nothing."""
    p, test = await _mine(db, user_id)
    where = await stage(db, p, test)
    if ended_at(p, which) is not None:
        return
    if where not in _open_stages(which) or started_at(p, which) is None:
        raise NotOpen(f"the {_prefix(which)} is not running")
    await end_test(db, p, test, which, utcnow(), "submitted")
    await db.commit()


async def close_for(db: AsyncSession, participants: list[Participant], at: datetime) -> None:
    """A batch closing ends every test still running in it. The caller commits."""
    for p in participants:
        test = await class_test(db, p.class_id)
        if test is None:
            continue
        for which in WHICH:
            await end_test(db, p, test, which, at, "closed")


# --------------------------------------------------------------------------- #
# scores


def scores(test: Test, answers: list[TrialAnswer]) -> dict:
    """A participant's pre-test score, post-test total and calibration.

    Each is None until everything it depends on is scored. Calibration is the
    share of ticked answers whose tick matched the result: "sure" with full
    marks, or "not sure" without.
    """
    got = {(a.test, a.item): a for a in answers}

    def total(which: str) -> int | None:
        marks = [getattr(got.get((which, i.id)), "score", None) for i in test.items(which) if i.scored]
        return None if any(m is None for m in marks) else sum(marks)

    ticked = []
    for item in test.posttest:
        a = got.get((POST, item.id))
        if item.ticked and a is not None and a.sure is not None:
            ticked.append((a.sure, a.score, item.points))
    calibration = sure_but_wrong = None
    if ticked and all(score is not None for _, score, _ in ticked):
        matches = sum(1 for sure, score, full in ticked if sure == (score == full))
        calibration = round(matches / len(ticked), 3)
        sure_but_wrong = sum(1 for sure, score, full in ticked if sure and score < full)
    return {
        "pretest_score": total(PRE),
        "posttest_total": total(POST),
        "calibration": calibration,
        "sure_but_wrong": sure_but_wrong,
    }


def left_to_grade(p: Participant, test: Test, answers: list[TrialAnswer]) -> int:
    """Written answers in ended tests that still need the grader."""
    got = {(a.test, a.item): a for a in answers}
    left = 0
    for which in WHICH:
        if ended_at(p, which) is None:
            continue
        for item in test.items(which):
            if item.graded_by_hand and getattr(got.get((which, item.id)), "score", None) is None:
                left += 1
    return left


# --------------------------------------------------------------------------- #
# grading


async def _gradable(db: AsyncSession) -> list[tuple[Participant, Test]]:
    rows = (
        await db.execute(
            select(Participant, Class.test_key)
            .join(Class, Class.id == Participant.class_id)
            .where(Class.test_key.is_not(None), Participant.pretest_ended_at.is_not(None))
            .order_by(Participant.code)
        )
    ).all()
    return [(p, trial_tests.get(key)) for p, key in rows if trial_tests.get(key) is not None]


async def grading_list(db: AsyncSession) -> list[dict]:
    """Everyone with a test to grade, by ID only. Never the group."""
    trial_service.require_trial()
    out = []
    for p, test in await _gradable(db):
        await expire(db, p, test)
        answers = await _answers(db, p.id)
        out.append(
            {
                "code": p.code,
                "left": left_to_grade(p, test, answers),
                "posttest_ended": p.posttest_ended_at is not None,
            }
        )
    return out


async def _participant(db: AsyncSession, code: str) -> tuple[Participant, Test]:
    trial_service.require_trial()
    p = await db.scalar(
        select(Participant).where(Participant.code == trial_service.normalize_code(code))
    )
    if p is None:
        raise NotGradable
    test = await class_test(db, p.class_id)
    if test is None or p.pretest_ended_at is None:
        raise NotGradable
    await expire(db, p, test)
    return p, test


async def grading_detail(db: AsyncSession, code: str) -> dict:
    """One participant's answers, scores and rubrics, by ID only."""
    p, test = await _participant(db, code)
    answers = await _answers(db, p.id)
    got = {(a.test, a.item): a for a in answers}

    def written(which: str, item: Item) -> dict:
        a = got.get((which, item.id))
        return {
            "test": which,
            "item": item.id,
            "question": item.question,
            "text": a.text if a else None,
            "parts": (
                [{"key": k, "prompt": v, "text": ((a.parts or {}).get(k) if a else None)}
                 for k, v in item.steps.items()]
                if item.kind == "steps" else None
            ),
            "sure": a.sure if a else None,
            "score": a.score if a else None,
            "points": item.points,
            "reference": item.reference,
            "criteria": [{"points": k, "text": v} for k, v in sorted(item.criteria.items(), reverse=True)],
        }

    out_written = []
    if ended_at(p, PRE) is not None:
        out_written.append(written(PRE, test.pretest))
    choices, sets = [], []
    if ended_at(p, POST) is not None:
        for item in test.posttest:
            a = got.get((POST, item.id))
            if item.kind == "choice":
                choices.append(
                    {
                        "item": item.id,
                        "choice": a.choice if a else None,
                        "answer": item.answer,
                        "correct": bool(a and a.choice == item.answer),
                        "sure": a.sure if a else None,
                    }
                )
            elif item.kind == "truefalse":
                marks = (a.parts if a else None) or {}
                sets.append(
                    {
                        "item": item.id,
                        "question": item.question,
                        "sure": a.sure if a else None,
                        "score": _tf_score(item, marks),
                        "points": item.points,
                        "statements": [
                            {"key": k, "text": st.text, "answer": st.answer, "picked": marks.get(k)}
                            for k, st in item.statements.items()
                        ],
                    }
                )
            elif item.graded_by_hand:
                out_written.append(written(POST, item))
    return {
        "code": p.code,
        "posttest_ended": ended_at(p, POST) is not None,
        "left": left_to_grade(p, test, answers),
        **scores(test, answers),
        "choices": choices,
        "sets": sets,
        "written": out_written,
    }


async def set_score(db: AsyncSession, code: str, which: str, item_id: str, score: int) -> dict:
    """The grader's score for one written answer. It can be changed any time."""
    p, test = await _participant(db, code)
    item = test.item(which, item_id)
    if item is None or not item.graded_by_hand:
        raise BadScore("this question is not graded by hand")
    if ended_at(p, which) is None:
        raise NotGradable
    if not 0 <= score <= item.points:
        raise BadScore(f"the score must be from 0 to {item.points}")
    row = await db.scalar(
        select(TrialAnswer).where(
            TrialAnswer.participant_id == p.id,
            TrialAnswer.test == which,
            TrialAnswer.item == item_id,
        )
    )
    if row is None:
        row = TrialAnswer(participant_id=p.id, test=which, item=item_id)
        db.add(row)
    row.score, row.scored_at = score, utcnow()
    await db.commit()
    return await grading_detail(db, code)
