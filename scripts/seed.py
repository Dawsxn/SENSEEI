#!/usr/bin/env python3
"""Fill the local database with the demo: one instructor, three classes, four
students, two readings, and sessions that show every state the app has.

    docker compose up -d --wait
    alembic upgrade head
    python scripts/seed.py

What it sets up, and what each piece is there to show:

- **DEMO_CLASS_1** has all four students and both readings. Its sessions cover
  a clean pass, a student flagged after running out of tries (Mariel), a flag
  cleared by a later pass with the earlier attempt still marked (Paolo), and a
  session left partway (Anthony).
- **Dawson Catignas** has no sessions, so a live one can be run from a clean
  start. He is also in DEMO_CLASS_2, which shares the trial reading, so a reading
  and a student each sit in two classes.
- **DEMO_CLASS_3** has the trial reading and no students: the empty states, and a
  class to join with its code.

The readings:

- **Strategic Offensives** is the reading the trial used. Its PDF and text are
  not published with this repository, so the seed reads them from
  `scripts/fixtures/local/` (ignored by git) and leaves the reading and its
  sessions out when they are not there.
- **Recovery to the Bisector** is written for this repository. Its figures carry
  detail the prose does not, which is what makes it a test of a student who
  answers by pointing at one.

**The sessions are scripted, not generated.** `scripts/fixtures/demo_sessions.yaml`
holds every answer, judgment and tutor reply, written for the demo in the style
of real sessions. Nothing here calls an LLM, and the seed costs nothing to run.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.rubric import criteria_for, load_rubric
from backend.db import dispose, sessionmaker
from backend.models import (
    STEP_ORDER,
    Assessment,
    Attempt,
    Class,
    CoreComponent,
    CriterionJudgment,
    Enrolment,
    Reading,
    ReadingAssignment,
    ReadingFile,
    Role,
    SeeiStep,
    Session,
    SessionStatus,
    TutorMessage,
    User,
    Verdict,
)
from backend.settings import get_settings

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "scripts" / "fixtures"
#: Readings that cannot be published, read from here when present.
LOCAL = FIXTURES / "local"
PDFS = FIXTURES / "readings"
SESSIONS_FILE = FIXTURES / "demo_sessions.yaml"

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

#: The attempt limit lives with the loop it governs, in the Orchestrator, so the
#: seeded sessions cannot disagree with how the live loop behaves.
from backend.orchestrator import MAX_ATTEMPTS as ATTEMPT_LIMIT  # noqa: E402
from backend.orchestrator import MOVES  # noqa: E402

RUBRIC_VERSION = "v3"

#: Readings get deterministic ids, derived from their slug, so the same reading
#: keeps the same id across reseeds. Everything else stays random.
SEED_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "seed.senseei.dlsu")


def reading_id(slug: str) -> uuid.UUID:
    """The stable id for a seeded reading."""
    return uuid.uuid5(SEED_NAMESPACE, slug)


INSTRUCTOR = ("Thomas Tiam-Lee", "thomas_tiamlee@dlsu.edu.ph")

STUDENTS = [
    ("Dawson Catignas", "dawson_catignas@dlsu.edu.ph"),
    ("Mariel Tamondong", "mariel_tamondong@dlsu.edu.ph"),
    ("Paolo Cruzado", "paolo_cruzado@dlsu.edu.ph"),
    ("Anthony Baybayon", "anthony_baybayon@dlsu.edu.ph"),
]

#: Name, section and join code. Placeholders, so nothing reads as a real course.
CLASSES = [
    ("DEMO_CLASS_1", "S01", "DEMA-2345"),
    ("DEMO_CLASS_2", "S02", "DEMB-2345"),
    ("DEMO_CLASS_3", "S03", "DEMC-2345"),
]

#: Student index to the classes they are in, by index into CLASSES.
ENROLMENTS = {0: [0, 1], 1: [0], 2: [0], 3: [0]}

#: How long ago the students joined: before every scripted session.
ENROLLED_DAYS_AGO = 14

#: Reading slug to the classes it is assigned to.
ASSIGNMENTS = {
    "strategic_offensives": [0, 1, 2],
    "tennis_recovery": [0],
}

TRIAL_READING = {
    "slug": "strategic_offensives",
    "title": "Strategic Offensives",
    "description": "When and how a company attacks its rivals",
}

#: Its PDF carries two diagrams whose detail the prose does not repeat. The
#: student sees the diagram, the Assessment Agent sees the bracketed description
#: of it in `content`, and the grade should come out the same.
TENNIS = {
    "slug": "tennis_recovery",
    "title": "Recovery to the Bisector",
    "description": "Where to stand between shots in tennis",
    "components": [
        "After hitting, the player recovers to the line that bisects the angle "
        "of the opponent's possible replies, not to the centre of the court.",
        "That bisector is drawn from the ball, so the correct recovery point "
        "moves every time the ball does.",
    ],
}

#: Manila, where the demo is shown: a session's `at` is a local time of day.
MANILA = timezone(timedelta(hours=8))


# ---------------------------------------------------------------------------
# loading


def _trial_reading() -> dict | None:
    """The trial reading from the local folder, or None when it is not there.

    The text is the instructor's checked copy when present, and otherwise what
    the PDF yields on its own, without figure descriptions.
    """
    slug = TRIAL_READING["slug"]
    pdf = LOCAL / f"{slug}.pdf"
    components = LOCAL / f"{slug}.components.txt"
    if not pdf.exists() or not components.exists():
        return None
    text_file = LOCAL / f"{slug}.txt"
    data = pdf.read_bytes()
    if text_file.exists():
        content = text_file.read_text(encoding="utf-8").strip()
    else:
        from backend.services.pdf_text import extract_pages_text, to_text

        content = to_text(extract_pages_text(data))
    return {
        "title": TRIAL_READING["title"],
        "description": TRIAL_READING["description"],
        "content": content,
        "components": [
            line.strip()
            for line in components.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ],
        "pdf": data,
    }


def load_readings() -> dict[str, dict]:
    """The readings the seed can find, by slug."""
    out: dict[str, dict] = {}
    trial = _trial_reading()
    if trial is not None:
        out[TRIAL_READING["slug"]] = trial
    else:
        print(
            f"note: {TRIAL_READING['title']} not found in {LOCAL}; "
            "seeding without it and its sessions."
        )

    tennis_pdf = PDFS / f"{TENNIS['slug']}.pdf"
    out[TENNIS["slug"]] = {
        "title": TENNIS["title"],
        "description": TENNIS["description"],
        "content": (PDFS / f"{TENNIS['slug']}.txt").read_text(encoding="utf-8").strip(),
        "components": TENNIS["components"],
        "pdf": tennis_pdf.read_bytes() if tennis_pdf.exists() else None,
    }
    return out


def load_sessions() -> list[dict]:
    """The scripted sessions, checked against the rubric they are graded on."""
    sessions = yaml.safe_load(SESSIONS_FILE.read_text(encoding="utf-8"))["sessions"]
    for n, spec in enumerate(sessions, start=1):
        for step in spec["steps"]:
            known = criteria_for(step["step"])
            for t in step["tries"]:
                unknown = set(t.get("fail") or {}) - set(known)
                if unknown:
                    raise SystemExit(
                        f"session {n}, {step['step']}: {sorted(unknown)} are not "
                        f"{step['step']} criteria in rubric {RUBRIC_VERSION}."
                    )
            if len(step["tries"]) > ATTEMPT_LIMIT:
                raise SystemExit(f"session {n}, {step['step']}: over {ATTEMPT_LIMIT} tries.")
    return sessions


# ---------------------------------------------------------------------------
# building rows


def _status(spec: dict) -> SessionStatus:
    """What a scripted session's tries add up to."""
    if spec.get("end") == "left":
        return SessionStatus.LEFT
    last = spec["steps"][-1]
    if last["tries"][-1].get("fail"):
        if len(last["tries"]) < ATTEMPT_LIMIT:
            raise SystemExit("a session ends on a failed try with tries left; mark it `end: left`.")
        return SessionStatus.FALLBACK
    if len(spec["steps"]) == len(STEP_ORDER):
        return SessionStatus.COMPLETE
    raise SystemExit("a session stops after a passed step; mark it `end: left`.")


def build_session(student: User, reading: Reading, spec: dict) -> list:
    """One scripted session and everything hanging off it, as a flat list of rows."""
    settings = get_settings()
    hour, minute = (int(x) for x in spec["at"].split(":"))
    local = datetime.now(MANILA).replace(hour=hour, minute=minute, second=0, microsecond=0)
    started = (local - timedelta(days=spec["days_ago"])).astimezone(timezone.utc)
    status = _status(spec)

    sess = Session(
        student_id=student.id,
        reading_id=reading.id,
        status=status,
        current_step=SeeiStep(spec["steps"][-1]["step"]),
        started_at=started,
        ended_at=None,
        rubric_version=RUBRIC_VERSION,
        tutor_prompt_version=settings.tutor_prompt_version,
        assessment_prompt_version=settings.assessment_prompt_version,
        llm_model=settings.llm_model,
    )
    rows: list = [sess]
    clock = started

    for step_spec in spec["steps"]:
        step = SeeiStep(step_spec["step"])
        clock += timedelta(seconds=6)
        rows.append(
            TutorMessage(
                session_id=sess.id,
                step=step,
                attempt_id=None,
                moves=MOVES["first_attempt"],
                content=step_spec["prompt"].strip(),
                created_at=clock,
            )
        )

        for number, t in enumerate(step_spec["tries"], start=1):
            answer = t["answer"].strip()
            failed = t.get("fail") or {}
            # time to think and type, longer for a longer answer
            clock += timedelta(seconds=45 + 2 * len(answer.split()))
            attempt = Attempt(
                session_id=sess.id,
                step=step,
                attempt_number=number,
                response_text=answer,
                submitted_at=clock,
            )
            rows.append(attempt)

            verdict = Verdict.FAIL if failed else Verdict.PASS
            assessment = Assessment(
                attempt_id=attempt.id,
                verdict=verdict,
                model_verdict=verdict.value,
                raw_response="; ".join(f"{c}: {r.strip()}" for c, r in failed.items())
                or "Every criterion met.",
                warnings=[],
                usage={
                    "input_tokens": 1800 + len(answer.split()) * 4,
                    "thinking_tokens": 220,
                    "output_tokens": 240,
                },
                created_at=clock + timedelta(seconds=4),
            )
            rows.append(assessment)
            for criterion in criteria_for(step.value):
                rows.append(
                    CriterionJudgment(
                        assessment_id=assessment.id,
                        criterion=criterion,
                        passed=criterion not in failed,
                        reason=failed[criterion].strip() if criterion in failed else None,
                    )
                )

            if not failed:
                situation = "passed"
            elif number >= ATTEMPT_LIMIT:
                situation = "final_fail"
            else:
                situation = "retry"
            clock += timedelta(seconds=7)
            rows.append(
                TutorMessage(
                    session_id=sess.id,
                    step=step,
                    attempt_id=attempt.id,
                    moves=MOVES[situation],
                    content=t["reply"].strip(),
                    created_at=clock,
                )
            )

    if status is not SessionStatus.IN_PROGRESS:
        # a student who left is marked when they confirmed, a little after the
        # last message
        sess.ended_at = clock + timedelta(minutes=2 if status is SessionStatus.LEFT else 0)
    return rows


def build_everything() -> list:
    """Every row the seed inserts, in insertion order."""
    readings_data = load_readings()
    rows: list = []

    instructor = User(
        role=Role.INSTRUCTOR,
        name=INSTRUCTOR[0],
        email=INSTRUCTOR[1],
        google_sub="seed-instructor-1",
    )
    rows.append(instructor)

    classes = [
        Class(instructor_id=instructor.id, name=name, section=section, join_code=code)
        for name, section, code in CLASSES
    ]
    rows += classes

    students = [
        User(role=Role.STUDENT, name=name, email=email, google_sub=f"seed-student-{i + 1}")
        for i, (name, email) in enumerate(STUDENTS)
    ]
    rows += students
    for student_index, class_indexes in ENROLMENTS.items():
        for c in class_indexes:
            # joined before the term's first session, so no session predates it
            rows.append(
                Enrolment(
                    student_id=students[student_index].id,
                    class_id=classes[c].id,
                    enrolled_at=datetime.now(timezone.utc) - timedelta(days=ENROLLED_DAYS_AGO),
                )
            )

    readings: dict[str, Reading] = {}
    for slug, data in readings_data.items():
        reading = Reading(
            id=reading_id(slug),
            uploaded_by=instructor.id,
            title=data["title"],
            description=data["description"],
            content=data["content"],
        )
        readings[slug] = reading
        rows.append(reading)
        if data["pdf"] is not None:
            rows.append(
                ReadingFile(
                    reading_id=reading.id,
                    filename=f"{slug}.pdf",
                    byte_size=len(data["pdf"]),
                    data=data["pdf"],
                )
            )
        for position, component in enumerate(data["components"]):
            rows.append(CoreComponent(reading_id=reading.id, text=component, position=position))
        for c in ASSIGNMENTS[slug]:
            rows.append(ReadingAssignment(reading_id=reading.id, class_id=classes[c].id))

    for spec in load_sessions():
        if spec["reading"] in readings:
            rows += build_session(students[spec["student"]], readings[spec["reading"]], spec)

    return rows


# ---------------------------------------------------------------------------
# running


#: The tables in dependency order. Rows are inserted one wave at a time with a
#: flush between waves, so a child never references a parent that has not been
#: written yet. A single add_all leaves the ordering to the unit of work, which
#: batches by table and, with client-generated UUIDs and no ORM relationships,
#: does not reliably put a parent before its child.
INSERT_WAVES: tuple[tuple[type, ...], ...] = (
    (User,),
    (Class, Reading),
    (Enrolment, CoreComponent, ReadingAssignment, ReadingFile, Session),
    (Attempt,),
    (Assessment,),
    (CriterionJudgment, TutorMessage),
)


async def insert_in_waves(session: AsyncSession, rows: list) -> None:
    """Add rows wave by wave, flushing between, so foreign keys always resolve."""
    by_type: dict[type, list] = defaultdict(list)
    for row in rows:
        by_type[type(row)].append(row)

    placed = 0
    for wave in INSERT_WAVES:
        batch = [row for model in wave for row in by_type.get(model, [])]
        if batch:
            session.add_all(batch)
            await session.flush()
            placed += len(batch)

    if placed != len(rows):
        raise SystemExit(
            f"insert waves placed {placed} of {len(rows)} rows; a model is "
            f"missing from INSERT_WAVES."
        )


async def wipe(session: AsyncSession) -> None:
    """Delete every seeded row.

    Deleting users is enough: classes, readings and sessions all cascade from
    them, and everything else cascades from those. If this ever stops being
    true, a foreign key has lost its ON DELETE CASCADE.
    """
    await session.execute(delete(User))
    await session.commit()


async def count_rows(session: AsyncSession) -> list[tuple[str, int]]:
    models = [
        User,
        Class,
        Enrolment,
        Reading,
        CoreComponent,
        ReadingAssignment,
        ReadingFile,
        Session,
        Attempt,
        Assessment,
        CriterionJudgment,
        TutorMessage,
    ]
    out = []
    for model in models:
        n = await session.scalar(select(func.count()).select_from(model))
        out.append((model.__tablename__, n or 0))
    return out


async def main() -> None:
    ap = argparse.ArgumentParser(description="Seed the local database.")
    ap.add_argument("--reset", action="store_true", help="delete existing rows first")
    ap.add_argument(
        "--force",
        action="store_true",
        help="allow running against a non-local environment",
    )
    ap.add_argument(
        "--if-empty",
        action="store_true",
        help="seed only if there are no users yet, and otherwise do nothing; "
        "what a deploy runs on every start",
    )
    args = ap.parse_args()

    settings = get_settings()
    if settings.environment != "local" and not args.force:
        raise SystemExit(
            f"environment is {settings.environment!r}, not 'local'. This script "
            f"writes fake users and deletes rows; pass --force if you are certain."
        )

    load_rubric(ROOT / "agents" / "rubrics" / f"rubric_{RUBRIC_VERSION}.yaml")

    async with sessionmaker()() as session:
        existing = await session.scalar(select(func.count()).select_from(User))
        if existing and args.if_empty:
            print(f"{existing} users already exist; not seeding.")
            await dispose()
            return
        if existing and not args.reset:
            raise SystemExit(
                f"{existing} users already exist. Re-run with --reset to replace them."
            )
        if args.reset:
            await wipe(session)

        await insert_in_waves(session, build_everything())
        await session.commit()

        print(f"seeded {settings.database_url.rsplit('/', 1)[-1]}")
        for table, n in await count_rows(session):
            print(f"  {table:<20} {n:>5}")

    await dispose()


if __name__ == "__main__":
    asyncio.run(main())
