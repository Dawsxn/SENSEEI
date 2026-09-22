"""An instructor's readings: upload in two calls, then manage.

Signed in through the dev bypass, like the class tests, because who may do what
is part of what is under test. The figure describer is replaced with a stub so
these tests never reach a provider.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pypdf import PdfWriter
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agents.figures import Figure, FigureResult
from backend.deps import get_figure_describer_dep
from backend.models import (
    Class,
    CoreComponent,
    Enrolment,
    Reading,
    ReadingFile,
    Role,
    User,
)

pytestmark = pytest.mark.usefixtures("fresh_engine")

TENNIS = (
    Path(__file__).resolve().parent.parent
    / "scripts" / "fixtures" / "readings" / "tennis_recovery.pdf"
).read_bytes()


def blank_pdf() -> bytes:
    """A real PDF with nothing on it: what a scanned page looks like to extraction."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


class StubDescriber:
    def __init__(self, result: FigureResult):
        self.result = result

    def describe(self, pdf: bytes, text: str) -> FigureResult:
        return self.result


@pytest.fixture
def describer():
    """Describes one figure unless a test swaps the result."""
    from backend.main import app

    stub = StubDescriber(
        FigureResult(
            figures=[
                Figure(
                    description="A court seen from above.",
                    label="Figure 6.4",
                    caption="Figure 6.4 The reply cone and its bisector.",
                    page=1,
                )
            ]
        )
    )
    app.dependency_overrides[get_figure_describer_dep] = lambda: stub
    yield stub
    app.dependency_overrides.pop(get_figure_describer_dep, None)


@pytest.fixture
async def people(point_app_at_test_db):
    """Two instructors, a class each for the first, and a student in both."""
    engine = create_async_engine(point_app_at_test_db)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(delete(User))
        await s.commit()

        prof = User(role=Role.INSTRUCTOR, name="Prof", email="prof@dlsu.edu.ph", google_sub="p1")
        other = User(role=Role.INSTRUCTOR, name="Other", email="other@dlsu.edu.ph", google_sub="p2")
        stu = User(role=Role.STUDENT, name="Stu", email="stu@dlsu.edu.ph", google_sub="s1")
        s.add_all([prof, other, stu])
        await s.flush()
        a = Class(instructor_id=prof.id, name="STRAMA", section="K31", join_code="4KQ2-9TXM")
        b = Class(instructor_id=prof.id, name="STSWENG", section="S11", join_code="7HWP-3CNE")
        theirs = Class(instructor_id=other.id, name="OTHER", section="X1", join_code="2222-3333")
        s.add_all([a, b, theirs])
        await s.flush()
        s.add_all([
            Enrolment(student_id=stu.id, class_id=a.id),
            Enrolment(student_id=stu.id, class_id=b.id),
        ])
        await s.commit()
        ids = {
            "prof": prof.id, "other": other.id, "stu": stu.id,
            "a": a.id, "b": b.id, "theirs": theirs.id,
        }
    await engine.dispose()
    return ids


@asynccontextmanager
async def signed_in(user_id):
    from backend.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/auth/dev/login", json={"user_id": str(user_id)})
        assert r.status_code == 200
        yield client


def upload(pdf: bytes = TENNIS, name: str = "tennis.pdf") -> dict:
    return {"file": (name, pdf, "application/pdf")}


def form(*class_ids, components=("Recover to the bisector.", "It moves with the ball.")) -> dict:
    return {
        "title": " Recovery ",
        "description": "Where to stand",
        "content": "The text as the instructor corrected it.",
        "core_components": list(components),
        "class_ids": [str(c) for c in class_ids],
    }


async def save(client, *class_ids, **kw) -> str:
    r = await client.post("/instructor/readings", files=upload(), data=form(*class_ids, **kw))
    assert r.status_code == 201, r.text
    return r.json()["id"]


# --------------------------------------------------------------------------- #
# step one: extract


@pytest.mark.anyio
async def test_extract_returns_the_text_with_figures_in_place_and_saves_nothing(people, describer, point_app_at_test_db):
    async with signed_in(people["prof"]) as prof:
        r = await prof.post("/instructor/readings/extract", files=upload())
    assert r.status_code == 200
    body = r.json()
    paragraphs = body["text"].split("\n\n")
    at = paragraphs.index("[Figure 6.4: A court seen from above.]")
    assert paragraphs[at + 1].startswith("Figure 6.4 The reply cone")
    assert (body["figures_described"], body["figures_failed"]) == (1, False)

    engine = create_async_engine(point_app_at_test_db)
    async with async_sessionmaker(engine)() as s:
        assert (await s.scalars(select(Reading))).all() == []
    await engine.dispose()


@pytest.mark.anyio
async def test_when_figures_cannot_be_described_the_text_still_comes_back(people, describer):
    describer.result = FigureResult(error="provider down")
    async with signed_in(people["prof"]) as prof:
        body = (await prof.post("/instructor/readings/extract", files=upload())).json()
    assert body["figures_failed"] is True and body["figures_described"] == 0
    assert "Between one shot and the next" in body["text"]


@pytest.mark.anyio
async def test_extract_refuses_what_it_cannot_read(people, describer):
    async with signed_in(people["prof"]) as prof:
        not_pdf = await prof.post("/instructor/readings/extract", files=upload(b"hello", "notes.txt"))
        no_text = await prof.post("/instructor/readings/extract", files=upload(blank_pdf()))
        too_big = await prof.post(
            "/instructor/readings/extract", files=upload(b"%PDF-" + b"0" * (20 * 1024 * 1024))
        )
    assert (not_pdf.status_code, not_pdf.json()["detail"]) == (415, "not_pdf")
    assert (no_text.status_code, no_text.json()["detail"]) == (422, "no_text")
    assert (too_big.status_code, too_big.json()["detail"]) == (413, "too_large")


@pytest.mark.anyio
async def test_students_cannot_upload(people, describer):
    async with signed_in(people["stu"]) as stu:
        assert (await stu.post("/instructor/readings/extract", files=upload())).status_code == 403
        assert (await stu.get("/instructor/readings")).status_code == 403


# --------------------------------------------------------------------------- #
# step two: save


@pytest.mark.anyio
async def test_saving_stores_the_corrected_text_file_and_components(people, point_app_at_test_db):
    async with signed_in(people["prof"]) as prof:
        rid = await save(prof, people["a"])
        detail = (await prof.get(f"/instructor/readings/{rid}")).json()
        file = await prof.get(f"/instructor/readings/{rid}/file")

    assert detail["title"] == "Recovery"
    assert detail["content"] == "The text as the instructor corrected it."
    assert detail["core_components"] == ["Recover to the bisector.", "It moves with the ball."]
    assert [c["label"] for c in detail["classes"]] == ["STRAMA K31"]
    assert detail["has_file"] is True
    assert file.status_code == 200 and file.content == TENNIS


@pytest.mark.anyio
async def test_a_reading_needs_a_core_component(people):
    async with signed_in(people["prof"]) as prof:
        r = await prof.post(
            "/instructor/readings", files=upload(), data=form(people["a"], components=("  ",))
        )
    assert (r.status_code, r.json()["detail"]) == (422, "no_core_components")


@pytest.mark.anyio
async def test_another_instructors_class_cannot_be_assigned(people):
    async with signed_in(people["prof"]) as prof:
        r = await prof.post("/instructor/readings", files=upload(), data=form(people["theirs"]))
        listed = (await prof.get("/instructor/readings")).json()
    assert (r.status_code, r.json()["detail"]) == (422, "unknown_class")
    assert listed == []  # and nothing half-saved


@pytest.mark.anyio
async def test_an_unassigned_reading_is_saved_but_no_student_sees_it(people):
    async with signed_in(people["prof"]) as prof:
        await save(prof)
        listed = (await prof.get("/instructor/readings")).json()
    assert [(r["title"], r["classes"], r["session_count"]) for r in listed] == [("Recovery", [], 0)]
    async with signed_in(people["stu"]) as stu:
        assert (await stu.get("/readings")).json() == []


@pytest.mark.anyio
async def test_a_student_in_two_of_its_classes_sees_it_once(people):
    async with signed_in(people["prof"]) as prof:
        await save(prof, people["a"], people["b"])
    async with signed_in(people["stu"]) as stu:
        rows = (await stu.get("/readings")).json()
    assert [(r["title"], r["class_name"]) for r in rows] == [("Recovery", "STRAMA K31")]


# --------------------------------------------------------------------------- #
# after saving


@pytest.mark.anyio
async def test_the_text_and_components_cannot_be_changed(people, point_app_at_test_db):
    async with signed_in(people["prof"]) as prof:
        rid = await save(prof, people["a"])
        r = await prof.patch(
            f"/instructor/readings/{rid}",
            json={"title": "Renamed", "description": "", "content": "rewritten", "core_components": ["x"]},
        )
    assert r.status_code == 200
    body = r.json()
    assert (body["title"], body["description"]) == ("Renamed", None)
    assert body["content"] == "The text as the instructor corrected it."
    assert body["core_components"] == ["Recover to the bisector.", "It moves with the ball."]


@pytest.mark.anyio
async def test_changing_classes_changes_who_sees_it(people):
    async with signed_in(people["prof"]) as prof:
        rid = await save(prof, people["a"])
        r = await prof.put(f"/instructor/readings/{rid}/classes", json={"class_ids": []})
        assert r.json()["classes"] == []
    async with signed_in(people["stu"]) as stu:
        assert (await stu.get("/readings")).json() == []

    async with signed_in(people["prof"]) as prof:
        r = await prof.put(f"/instructor/readings/{rid}/classes", json={"class_ids": [str(people["b"])]})
        assert [c["label"] for c in r.json()["classes"]] == ["STSWENG S11"]
    async with signed_in(people["stu"]) as stu:
        assert [row["class_name"] for row in (await stu.get("/readings")).json()] == ["STSWENG S11"]


@pytest.mark.anyio
async def test_deleting_takes_it_away_from_students(people):
    async with signed_in(people["prof"]) as prof:
        rid = await save(prof, people["a"])
        assert (await prof.delete(f"/instructor/readings/{rid}")).status_code == 204
        assert (await prof.get("/instructor/readings")).json() == []
        assert (await prof.get(f"/instructor/readings/{rid}")).status_code == 404
    async with signed_in(people["stu"]) as stu:
        assert (await stu.get("/readings")).json() == []
        assert (await stu.get(f"/readings/{rid}")).status_code == 404


@pytest.mark.anyio
async def test_another_instructors_reading_does_not_exist_for_you(people):
    async with signed_in(people["prof"]) as prof:
        rid = await save(prof, people["a"])
    async with signed_in(people["other"]) as other:
        assert (await other.get("/instructor/readings")).json() == []
        for r in (
            await other.get(f"/instructor/readings/{rid}"),
            await other.get(f"/instructor/readings/{rid}/file"),
            await other.patch(f"/instructor/readings/{rid}", json={"title": "Mine"}),
            await other.put(f"/instructor/readings/{rid}/classes", json={"class_ids": []}),
            await other.delete(f"/instructor/readings/{rid}"),
        ):
            assert r.status_code == 404
