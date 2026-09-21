#!/usr/bin/env python3
"""Fill the local database with data the app can be developed against.

    docker compose up -d --wait
    alembic upgrade head
    python scripts/seed.py

One instructor, two classes, five students, and four expository texts. Several students have real
sessions behind them, with attempts, assessments and per-criterion judgments, so
the instructor dashboard has something to return and its queries can be checked
against numbers a human can count.

Two things here are real rather than invented:

- **Three of the reading texts and their core components** come from the eval
  dataset, so the app and the eval harness study the same material. The fourth,
  the tennis reading, is written for this repository: it is the only one whose
  figures carry detail the prose does not, which is what makes it a test of
  grading a student who answers by pointing at one.
- **The student responses** are rows from that dataset too, each already
  labelled with the verdict it should get and the criteria it was written to
  fail. That is why the seeded pass/fail pattern is coherent rather than
  arbitrary.

**The tutor messages are written by this script, not by the Tutor Agent.** They
are stand-ins so the transcript view has something to render. Nothing here calls
an LLM, and the seed costs nothing to run.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
import uuid
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

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
    Session,
    SessionStatus,
    TutorMessage,
    User,
    Verdict,
    utcnow,
)
from backend.settings import get_settings

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "assessment-agent-eval" / "data"

#: The original PDFs of the seeded readings, named by slug. These are the real
#: documents the extracted text in the eval dataset came from, so what a seeded
#: student reads on screen is what the agents grade against.
PDFS = ROOT / "scripts" / "fixtures" / "readings"

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

#: The attempt limit lives with the loop it governs, in the Orchestrator, so the
#: seeded sessions cannot disagree with how the live loop behaves.
from backend.orchestrator import MAX_ATTEMPTS as ATTEMPT_LIMIT  # noqa: E402

RUBRIC_VERSION = "v3"

#: Readings get deterministic ids, derived from their slug, so the same reading
#: keeps the same id across reseeds. That gives the frontend a stable id to enter
#: a session with before a reading-list screen and its API exist. Everything else
#: (users, sessions, attempts) stays random.
SEED_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "seed.senseei.dlsu")


def reading_id(slug: str) -> uuid.UUID:
    """The stable id for a seeded reading. `strategy` is the frontend's dev entry."""
    return uuid.uuid5(SEED_NAMESPACE, slug)

TITLES = {
    "strategy": "Strategy",
    "business_model": "Business Model",
    "strategic_vision": "Strategic Vision",
}

#: One-line topic summaries, shown under the title in the reading list. The
#: instructor writes these on the upload screen once it exists; for now the seed
#: supplies them, in the same style as the mockup.
DESCRIPTIONS = {
    "strategy": "Coordinated actions to outperform rivals",
    "business_model": "Customer value proposition, profit formula",
    "strategic_vision": "Direction, market position, future course",
}

#: A fourth reading that is not from the eval dataset, and deliberately so.
#: Its PDF carries two diagrams whose detail the prose does not repeat, which is
#: the only way to check what happens when a student answers by pointing at a
#: figure: the student sees the diagram, the Assessment Agent sees the bracketed
#: description of it in `content`, and the grade should come out the same.
#:
#: Its text and PDF live beside the other fixtures. `content` here is what the
#: upload flow will one day produce automatically — extracted prose with each
#: figure written out in words, reviewed by the instructor before going live.
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

INSTRUCTOR = ("Prof. Reyes", "a.reyes@dlsu.edu.ph")

STUDENTS = [
    ("Mateo Cruz", "mateo_cruz@dlsu.edu.ph"),
    ("Bea Villanueva", "bea_villanueva@dlsu.edu.ph"),
    ("Nikko Tan", "nikko_tan@dlsu.edu.ph"),
    ("Chelsea Ocampo", "chelsea_ocampo@dlsu.edu.ph"),
    ("Rafael Lim", "rafael_lim@dlsu.edu.ph"),
]

#: Two different courses, not two sections of one. A student can be enrolled in
#: both, which is what gives the reading list's class filter something to filter
#: — and it cannot happen with two sections of the same course, where enrolment
#: in one excludes the other.
CLASSES = [("STSWENG", "S11", "7HWP-3CNE"), ("STRAMA", "K31", "4KQ2-9TXM")]

#: Which steps each seeded session gets, and the verdict of every attempt within
#: them. Outcomes are spread on purpose: a dashboard where everyone passes on
#: the first try proves nothing about the queries behind it.
PLANS: dict[str, list[list[str]]] = {
    # a clean run, four steps, first try each
    "clean": [["PASS"], ["PASS"], ["PASS"], ["PASS"]],
    # one stumble on State, recovered
    "one_retry": [["FAIL", "PASS"], ["PASS"], ["PASS"], ["PASS"]],
    # struggled in the middle
    "two_retries": [["PASS"], ["FAIL", "PASS"], ["FAIL", "FAIL", "PASS"], ["PASS"]],
    # attempts exhausted on State: ends in fallback, flags the instructor
    "fallback": [["FAIL", "FAIL", "FAIL"]],
    # stopped partway, still open
    "in_progress": [["PASS"], ["FAIL"]],
}

#: Student index, reading slug, plan, and how many days ago it happened.
#:
#: Every pair here must be one the student can actually see, or the session is
#: unreachable: the reading list derives its status through the same visibility
#: query, and the review screen lists sessions per reading the same way.
#:
#: The tennis reading has no sessions. Its responses would have to come from the
#: eval dataset, which does not cover it, and leaving it unattempted is also what
#: makes it the clean one to test a fresh session against.
SESSIONS = [
    (0, "business_model", "clean", 11),
    (1, "business_model", "one_retry", 10),
    (2, "business_model", "two_retries", 8),
    (2, "strategy", "fallback", 9),
    (3, "strategy", "clean", 7),
    (4, "strategy", "one_retry", 6),
    (3, "strategic_vision", "fallback", 4),
    (4, "strategic_vision", "two_retries", 3),
    # a second, abandoned attempt: not resumable, so it must read as not started
    (0, "business_model", "in_progress", 1),
]

MOVES = {
    "first": ["Prompt"],
    "retry": ["Acknowledgement", "Criterion-Based Feedback", "Re-Prompt"],
    "final_fail": ["Acknowledgement", "Criterion-Based Feedback"],
    "passed": ["Acknowledgement", "Transition"],
}


# ---------------------------------------------------------------------------
# the dataset


def load_readings() -> dict[str, dict]:
    """The four readings: text, core components and the original PDF.

    Three come from the eval dataset, keyed by the CSV's reading filename. The
    tennis reading is appended separately because it has no eval rows — it is a
    fixture for the figure-reference case, not study material.
    """
    csv_path = sorted(DATA.glob("example_set_v*.csv"))[-1]
    components: dict[str, str] = {}
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            components.setdefault(row["reading_filename"], row["core_components"])

    out: dict[str, dict] = {}
    for filename, comps in components.items():
        slug = filename.replace(".txt", "")
        if slug not in TITLES:
            continue  # a reading with no core components is not seeded
        text = (DATA / "readings" / filename).read_text(encoding="utf-8").strip()
        pdf = PDFS / f"{slug}.pdf"
        out[slug] = {
            "title": TITLES[slug],
            "description": DESCRIPTIONS.get(slug),
            "content": text,
            # several components are joined with || in the one CSV field
            "components": [c.strip() for c in comps.split("||") if c.strip()],
            # A reading without a PDF is not an error: it falls back to the text
            # view, which is what every reading does until the upload flow exists.
            "pdf": pdf.read_bytes() if pdf.exists() else None,
        }

    tennis_pdf = PDFS / f"{TENNIS['slug']}.pdf"
    out[TENNIS["slug"]] = {
        "title": TENNIS["title"],
        "description": TENNIS["description"],
        "content": (PDFS / f"{TENNIS['slug']}.txt").read_text(encoding="utf-8").strip(),
        "components": TENNIS["components"],
        "pdf": tennis_pdf.read_bytes() if tennis_pdf.exists() else None,
    }
    return out


def load_responses() -> dict[tuple[str, str, str], list[dict]]:
    """Student responses from the eval CSV, keyed by reading, step and verdict."""
    csv_path = sorted(DATA.glob("example_set_v*.csv"))[-1]
    out: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            key = (
                row["reading_filename"].replace(".txt", ""),
                row["seei_step"],
                row["expected_verdict"],
            )
            out[key].append(row)
    return out


def failed_criteria(row: dict, step: str) -> list[str]:
    """The criteria a FAIL row was written to break, as canonical names."""
    targeted = [c.strip() for c in row["criterion_targeted"].split("+") if c.strip()]
    known = criteria_for(step)
    for name in targeted:
        if name not in known:
            raise SystemExit(
                f"Dataset row {row['id']} targets {name!r}, which is not a {step} "
                f"criterion in rubric {RUBRIC_VERSION}. The dataset and the "
                f"rubric have drifted apart."
            )
    return targeted


# ---------------------------------------------------------------------------
# building rows


def tutor_text(kind: str, step: str, title: str, unmet: list[str]) -> str:
    """Stand-in copy. The real thing comes from the Tutor Agent at runtime."""
    named = ", ".join(unmet)
    if kind == "first":
        return (
            f"Let us work on {step}. In your own words, "
            f"{step.lower()} the concept of {title}."
        )
    if kind == "passed":
        return f"That meets the criteria for {step}. Moving on."
    if kind == "retry":
        return (
            f"That is an attempt, but it does not yet meet {named}. "
            f"Try {step.lower()} again with those in mind."
        )
    return (
        f"That attempt does not meet {named}, and there are no attempts "
        f"left for {step}."
    )


def build_session(
    student: User,
    reading: Reading,
    slug: str,
    plan_name: str,
    days_ago: int,
    responses: dict[tuple[str, str, str], list[dict]],
    picked: dict[tuple, int],
) -> list:
    """One session and everything hanging off it, as a flat list of rows."""
    plan = PLANS[plan_name]
    settings = get_settings()
    started = utcnow() - timedelta(days=days_ago)

    steps_done = len(plan)
    last = plan[-1]
    exhausted = len(last) >= ATTEMPT_LIMIT and last[-1] == "FAIL"
    finished_all = steps_done == len(STEP_ORDER) and last[-1] == "PASS"

    if exhausted:
        status = SessionStatus.FALLBACK
    elif finished_all:
        status = SessionStatus.COMPLETE
    else:
        status = SessionStatus.IN_PROGRESS

    sess = Session(
        student_id=student.id,
        reading_id=reading.id,
        status=status,
        current_step=STEP_ORDER[min(steps_done - 1, len(STEP_ORDER) - 1)],
        started_at=started,
        ended_at=(
            None
            if status is SessionStatus.IN_PROGRESS
            else started + timedelta(minutes=14)
        ),
        rubric_version=RUBRIC_VERSION,
        tutor_prompt_version=settings.tutor_prompt_version,
        assessment_prompt_version=settings.assessment_prompt_version,
        llm_model=settings.llm_model,
    )
    rows: list = [sess]
    clock = started

    for step_index, verdicts in enumerate(plan):
        step = STEP_ORDER[step_index]
        step_name = step.value

        # the question that opens the step
        clock += timedelta(seconds=20)
        rows.append(
            TutorMessage(
                session_id=sess.id,
                step=step,
                attempt_id=None,
                moves=MOVES["first"],
                content=tutor_text("first", step_name, reading.title, []),
                created_at=clock,
            )
        )

        for number, verdict in enumerate(verdicts, start=1):
            key = (slug, step_name, verdict)
            pool = responses.get(key) or []
            if not pool:
                raise SystemExit(f"No {verdict} response in the dataset for {key}")
            row = pool[picked[key] % len(pool)]
            picked[key] += 1

            clock += timedelta(minutes=2)
            attempt = Attempt(
                session_id=sess.id,
                step=step,
                attempt_number=number,
                response_text=row["user_response"],
                submitted_at=clock,
            )
            rows.append(attempt)

            unmet = failed_criteria(row, step_name) if verdict == "FAIL" else []
            words = max(len(row["user_response"].split()), 1)
            assessment = Assessment(
                attempt_id=attempt.id,
                verdict=Verdict(verdict),
                model_verdict=verdict,
                raw_response=row["rationale"],
                warnings=[],
                usage={
                    "input_tokens": 1400 + words * 4,
                    "thinking_tokens": 180,
                    "output_tokens": 210,
                },
                created_at=clock + timedelta(seconds=4),
            )
            rows.append(assessment)

            for criterion in criteria_for(step_name):
                rows.append(
                    CriterionJudgment(
                        assessment_id=assessment.id,
                        criterion=criterion,
                        passed=criterion not in unmet,
                        reason=row["rationale"] if criterion in unmet else None,
                    )
                )

            if verdict == "PASS":
                kind = "passed"
            elif number >= ATTEMPT_LIMIT:
                kind = "final_fail"
            else:
                kind = "retry"

            clock += timedelta(seconds=8)
            rows.append(
                TutorMessage(
                    session_id=sess.id,
                    step=step,
                    attempt_id=attempt.id,
                    moves=MOVES[kind],
                    content=tutor_text(kind, step_name, reading.title, unmet),
                    created_at=clock,
                )
            )

    return rows


def build_everything() -> list:
    """Every row the seed inserts, in insertion order."""
    readings_data = load_readings()
    responses = load_responses()
    picked: dict[tuple, int] = defaultdict(int)
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
        User(
            role=Role.STUDENT,
            name=name,
            email=email,
            google_sub=f"seed-student-{i + 1}",
        )
        for i, (name, email) in enumerate(STUDENTS)
    ]
    rows += students

    # first three in STSWENG, last three in STRAMA, so the middle student takes
    # both courses and sees the readings of each
    for student in students[:3]:
        rows.append(Enrolment(student_id=student.id, class_id=classes[0].id))
    for student in students[2:]:
        rows.append(Enrolment(student_id=student.id, class_id=classes[1].id))

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
            rows.append(
                CoreComponent(
                    reading_id=reading.id, text=component, position=position
                )
            )

    # Each reading belongs to exactly one class. Assigning one to both would
    # show it twice to the student enrolled in both, because visibility is
    # resolved per class: two rows for one reading.
    for class_index, slug in (
        (0, "business_model"),
        (0, "tennis_recovery"),
        (1, "strategy"),
        (1, "strategic_vision"),
    ):
        rows.append(
            ReadingAssignment(
                reading_id=readings[slug].id, class_id=classes[class_index].id
            )
        )

    for student_index, slug, plan_name, days_ago in SESSIONS:
        rows += build_session(
            students[student_index],
            readings[slug],
            slug,
            plan_name,
            days_ago,
            responses,
            picked,
        )

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
