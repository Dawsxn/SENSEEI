"""The trial's pre-test and post-test, and grading them (docs/context/trial.md).

A class takes a test when its setting names one; its participants then go
pre-test, session, post-test, each timed, with the server holding every rule.
Built on the trial tests' fixtures, with the team's reading renamed to the title
the strategic offensives test is written for.
"""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import timedelta

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.models import Participant, Reading, Role, TrialAnswer, User, utcnow
from backend.trial_tests import POST, PRE, load
from test_trial_api import (  # noqa: F401  (fixtures are used by name)
    _batch,
    _clear_overrides,
    _first,
    _three_groups,
    as_participant,
    as_user,
    team,
    trial_on,
)

pytestmark = pytest.mark.usefixtures("fresh_engine")

KEY = "strategic_offensives"


@pytest.fixture
async def setup(team, trial_on):
    """The three groups, all taking the test, a batch, and a grader."""
    engine = create_async_engine(trial_on)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(
            update(Reading).where(Reading.id == team["reading"]).values(title="Strategic Offensives")
        )
        grader = User(role=Role.GRADER, name="Grader", email="g@dlsu.edu.ph", google_sub="g1")
        s.add(grader)
        await s.commit()
        grader_id = grader.id
    await engine.dispose()

    async with as_user(team["prof"]) as prof:
        classes = await _three_groups(prof, team["reading"])
        for section, mode in (("S1-A", "seei"), ("S1-B", "chatbot"), ("S1-C", "reading_only")):
            r = await prof.patch(
                f"/instructor/classes/{classes[mode]}",
                json={"name": "TRIAL", "section": section, "mode": mode, "test_key": KEY},
            )
            assert r.status_code == 200, r.text
        batch = await _batch(prof, classes)
    return {
        "classes": classes,
        "batch": batch,
        "grader": grader_id,
        "url": trial_on,
        **{mode: _first(batch, mode)["code"] for mode in ("seei", "chatbot", "reading_only")},
    }


async def _move(url: str, code: str, **minutes_ago: int) -> None:
    """Pretend a clock started that many minutes ago, e.g. pretest_started_at=6."""
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.execute(
            update(Participant)
            .where(Participant.code == code)
            .values(**{k: utcnow() - timedelta(minutes=v) for k, v in minutes_ago.items()})
        )
    await engine.dispose()


async def _answers(url: str, code: str) -> dict:
    engine = create_async_engine(url)
    maker = async_sessionmaker(engine)
    async with maker() as s:
        rows = list(
            await s.scalars(
                select(TrialAnswer)
                .join(Participant, Participant.id == TrialAnswer.participant_id)
                .where(Participant.code == code)
            )
        )
    await engine.dispose()
    return {(a.test, a.item): a for a in rows}


async def _stage(client) -> str | None:
    return (await client.get("/trial/me")).json()["test_stage"]


async def _through_pretest(me, text="An aggressive move to take market share from rivals."):
    assert (await me.post("/trial/tests/pre/start")).status_code == 200
    assert (await me.put("/trial/tests/pre/answers/pre", json={"text": text})).status_code == 200
    r = await me.post("/trial/tests/pre/submit")
    assert r.status_code == 200, r.text
    return r.json()


async def _take_posttest(me, right: bool = True):
    test = load()[KEY]
    assert (await me.post("/trial/tests/post/start")).status_code == 200
    for item in test.posttest:
        if item.kind == "choice":
            pick = item.answer if right else next(k for k in item.options if k != item.answer)
            r = await me.put(f"/trial/tests/post/answers/{item.id}", json={"choice": pick, "sure": True})
        elif item.kind == "text":
            r = await me.put(f"/trial/tests/post/answers/{item.id}", json={"text": "Because of strengths.", "sure": False})
        else:
            r = await me.put(
                f"/trial/tests/post/answers/{item.id}",
                json={"groups": [{"name": "Price", "strategies": "lower price", "why": "cheaper"}]},
            )
        assert r.status_code == 200, r.text
    r = await me.post("/trial/tests/post/submit")
    assert r.status_code == 200, r.text


# --------------------------------------------------------------------------- #
# the test file


@pytest.mark.anyio
async def test_the_test_file_adds_up():
    test = load()[KEY]
    assert test.total(PRE) == 3
    assert test.total(POST) == 20
    assert sum(i.ticked for i in test.posttest) == 11
    assert test.pretest_minutes == 5 and test.posttest_minutes == 30


# --------------------------------------------------------------------------- #
# the class setting


@pytest.mark.anyio
async def test_a_test_is_offered_only_for_its_reading(team, trial_on):
    async with as_user(team["prof"]) as prof:
        classes = await _three_groups(prof, team["reading"])
        cid = classes["seei"]
        detail = (await prof.get(f"/instructor/classes/{cid}")).json()
        assert detail["tests"] == []          # the reading is titled for another test
        r = await prof.patch(
            f"/instructor/classes/{cid}",
            json={"name": "TRIAL", "section": "S1-A", "mode": "seei", "test_key": KEY},
        )
        assert r.status_code == 422
        r = await prof.post(
            "/instructor/classes",
            json={"name": "NEW", "section": "X", "mode": "seei", "test_key": KEY},
        )
        assert r.status_code == 422           # a new class has no reading yet


@pytest.mark.anyio
async def test_the_test_setting_locks_with_the_mode(setup, team):
    async with as_participant(setup["seei"]):
        pass
    async with as_user(team["prof"]) as prof:
        cid = setup["classes"]["seei"]
        detail = (await prof.get(f"/instructor/classes/{cid}")).json()
        assert detail["test_key"] == KEY and detail["mode_locked"]
        assert detail["tests"] == [{"key": KEY, "title": "Strategic Offensives"}]
        r = await prof.patch(
            f"/instructor/classes/{cid}",
            json={"name": "TRIAL", "section": "S1-A", "mode": "seei", "test_key": None},
        )
        assert r.status_code == 409


# --------------------------------------------------------------------------- #
# taking the tests


@pytest.mark.anyio
async def test_the_stages_run_in_order_and_the_server_holds_them(setup):
    async with as_participant(setup["reading_only"]) as me:
        assert await _stage(me) == "pretest"
        assert (await me.post("/trial/clock")).status_code == 409        # no reading yet
        assert (await me.get("/trial/tests/post")).status_code == 409    # nor the post-test
        view = (await me.get("/trial/tests/pre")).json()
        assert view["started"] is False and view["seconds_left"] is None
        assert "answer" not in str(view["items"]) and "criteria" not in str(view)

        status = await _through_pretest(me)
        assert status["test_stage"] == "session"
        # The welcome screen's step times come from the test file.
        assert status["test_minutes"] == {"pre": 5, "post": 30}
        assert (await me.put("/trial/tests/pre/answers/pre", json={"text": "late"})).status_code == 409

        assert (await me.post("/trial/clock")).status_code == 200
        assert (await me.post("/trial/done")).status_code == 200
        assert await _stage(me) == "posttest_ready"
        view = (await me.get("/trial/tests/post")).json()
        assert view["started"] is False and len(view["items"]) == 13

        await _take_posttest(me)
        assert await _stage(me) == "done"
        assert (await me.get("/trial/tests/post")).status_code == 409


@pytest.mark.anyio
async def test_a_test_that_runs_out_of_time_keeps_what_was_saved(setup):
    code = setup["chatbot"]
    async with as_participant(code) as me:
        await me.post("/trial/tests/pre/start")
        await me.put("/trial/tests/pre/answers/pre", json={"text": "half an answer"})
    await _move(setup["url"], code, pretest_started_at=6)
    async with as_participant(code) as me:
        assert await _stage(me) == "session"
    answers = await _answers(setup["url"], code)
    assert answers[("pre", "pre")].text == "half an answer"
    assert answers[("pre", "pre")].score is None          # written: for the grader


@pytest.mark.anyio
async def test_blank_answers_score_zero_when_a_test_ends(setup):
    code = setup["reading_only"]
    async with as_participant(code) as me:
        await _through_pretest(me, text="")
        await me.post("/trial/clock")
        await me.post("/trial/done")
        await me.post("/trial/tests/post/start")
        await me.put("/trial/tests/post/answers/q1", json={"choice": "a"})
        await me.post("/trial/tests/post/submit")
    answers = await _answers(setup["url"], code)
    assert answers[("pre", "pre")].score == 0
    assert answers[("post", "q1")].score == 0             # wrong choice
    assert answers[("post", "q5")].score == 0             # never answered
    assert ("post", "q12a") not in answers                # not scored, so not zeroed


@pytest.mark.anyio
async def test_each_answer_keeps_its_history(setup):
    code = setup["reading_only"]
    async with as_participant(code) as me:
        await _through_pretest(me)
        await me.post("/trial/clock")
        await me.post("/trial/done")
        await me.post("/trial/tests/post/start")
        for text in ("A", "AB", "AB"):                     # the last save changes nothing
            await me.put("/trial/tests/post/answers/q5", json={"text": text})
        await me.put("/trial/tests/post/answers/q5", json={"sure": True})
        assert (await me.put("/trial/tests/post/answers/q1", json={"choice": "z"})).status_code == 422
        assert (await me.put("/trial/tests/post/answers/q99", json={"text": "x"})).status_code == 404
    a = (await _answers(setup["url"], code))[("post", "q5")]
    assert a.edits == 2 and a.sure is True
    assert a.first_answered_at <= a.last_changed_at


@pytest.mark.anyio
async def test_finished_on_the_batch_page_means_the_posttest_is_in(setup, team):
    code = setup["reading_only"]
    async with as_participant(code) as me:
        await _through_pretest(me)
        await me.post("/trial/clock")
        await me.post("/trial/done")

    async def status():
        async with as_user(team["prof"]) as prof:
            batch = (await prof.get(f"/instructor/batches/{setup['batch']['id']}")).json()
        return next(p["status"] for p in batch["participants"] if p["code"] == code)

    assert await status() == "signed_in"                   # Done, but the post-test is next
    async with as_participant(code) as me:
        await _take_posttest(me)
    assert await status() == "finished"


@pytest.mark.anyio
async def test_closing_the_batch_ends_a_running_test(setup, team):
    code = setup["chatbot"]
    async with as_participant(code) as me:
        await me.post("/trial/tests/pre/start")
    async with as_user(team["prof"]) as prof:
        await prof.post(f"/instructor/batches/{setup['batch']['id']}/close")
    engine = create_async_engine(setup["url"])
    maker = async_sessionmaker(engine)
    async with maker() as s:
        p = await s.scalar(select(Participant).where(Participant.code == code))
    await engine.dispose()
    assert p.pretest_ended_by == "closed"


# --------------------------------------------------------------------------- #
# grading


@pytest.mark.anyio
async def test_the_grader_sees_ids_scores_and_rubrics_but_never_the_group(setup, team):
    code = setup["reading_only"]
    async with as_participant(code) as me:
        await _through_pretest(me)
        await me.post("/trial/clock")
        await me.post("/trial/done")
        await _take_posttest(me)

    async with as_user(setup["grader"]) as grader:
        assert (await grader.get("/instructor/batches")).status_code == 403
        assert (await grader.get("/instructor/export")).status_code == 403
        listed = (await grader.get("/instructor/grading")).json()
        assert listed == [{"code": code, "left": 9, "posttest_ended": True}]

        detail = (await grader.get(f"/instructor/grading/{code}")).json()
        assert "reading_only" not in str(detail) and "group" not in detail
        assert detail["posttest_total"] is None and detail["pretest_score"] is None
        assert all(c["correct"] for c in detail["choices"])
        assert detail["groups"][0]["name"] == "Price"
        written = {(w["test"], w["item"]): w for w in detail["written"]}
        assert written[("pre", "pre")]["points"] == 3
        assert written[("post", "q5")]["criteria"][0]["points"] == 2

        assert (await grader.put(f"/instructor/grading/{code}/post/q5", json={"score": 3})).status_code == 422
        assert (await grader.put(f"/instructor/grading/{code}/post/q1", json={"score": 1})).status_code == 422
        for (which, item), w in written.items():
            r = await grader.put(f"/instructor/grading/{code}/{which}/{item}", json={"score": w["points"]})
            assert r.status_code == 200, r.text
        done = r.json()

    assert done["left"] == 0
    assert done["pretest_score"] == 3
    assert done["posttest_total"] == 20
    # Every choice ticked "sure" and right; every written answer "not sure" but full marks.
    assert done["calibration"] == round(4 / 11, 3)
    assert done["sure_but_wrong"] == 0


@pytest.mark.anyio
async def test_the_export_has_the_tests(setup, team):
    code = setup["reading_only"]
    async with as_participant(code) as me:
        await _through_pretest(me)
        await me.post("/trial/clock")
        await me.post("/trial/done")
        await _take_posttest(me, right=False)
    async with as_user(team["prof"]) as prof:
        data = (await prof.get("/instructor/export")).content
    zf = zipfile.ZipFile(io.BytesIO(data))

    def rows(name):
        return list(csv.DictReader(io.StringIO(zf.read(name).decode("utf-8-sig"))))

    me = next(r for r in rows("participants.csv") if r["participant_id"] == code)
    assert me["test"] == KEY and me["pretest_ended_by"] == "submitted"
    assert me["posttest_ended_by"] == "submitted" and me["posttest_total"] == ""   # not graded yet
    tests = [r for r in rows("tests.csv") if r["participant_id"] == code]
    q1 = next(r for r in tests if r["question"] == "q1")
    assert q1["score"] == "0" and q1["sure"] == "True" and q1["dimension"] == "facts"
    assert q1["max_score"] == "1" and q1["edits"] == "1"


# --------------------------------------------------------------------------- #
# deleting a batch


@pytest.mark.anyio
async def test_a_batch_is_deleted_only_once_closed_and_takes_everything(setup, team):
    code = setup["reading_only"]
    async with as_participant(code) as me:
        await _through_pretest(me)
    batch = setup["batch"]["id"]
    async with as_user(team["prof"]) as prof:
        assert (await prof.delete(f"/instructor/batches/{batch}")).status_code == 409
        await prof.post(f"/instructor/batches/{batch}/close")
        assert (await prof.delete(f"/instructor/batches/{batch}")).status_code == 204
        assert (await prof.get(f"/instructor/batches/{batch}")).status_code == 404
    assert await _answers(setup["url"], code) == {}
