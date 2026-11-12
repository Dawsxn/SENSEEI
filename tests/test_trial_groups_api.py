"""The trial's control groups and its event log (docs/context/trial.md).

The chatbot group's conversation, Done for the two groups without a session, and
what gets recorded about what a participant did. Built on the trial tests'
fixtures; the chatbot is the mock provider unless a test swaps it.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agents.providers.base import LLMProvider
from agents.providers.mock import MockProvider
from backend.models import ChatMessage, Participant, TrialEvent, utcnow
from test_session_api import parse_sse
from test_trial_api import (  # noqa: F401  (fixtures are used by name)
    _batch,
    _clear_overrides,
    _first,
    _set_clock,
    _three_groups,
    as_participant,
    as_user,
    team,
    trial_on,
)

pytestmark = pytest.mark.usefixtures("fresh_engine")


class Recording(MockProvider):
    """The mock chatbot, remembering what it was sent."""

    def __init__(self):
        super().__init__({})
        self.sent: list[list[tuple[str, str]]] = []

    def chat_stream(self, turns):
        self.sent.append(list(turns))
        yield from super().chat_stream(turns)


class Broken(LLMProvider):
    def complete(self, system_prompt, user_prompt):
        raise RuntimeError("simulated outage")

    def chat_stream(self, turns):
        yield "Half a rep"
        raise RuntimeError("simulated outage mid-reply")


@pytest.fixture
def chatbot():
    from backend.deps import get_chatbot_dep
    from backend.main import app

    model = Recording()
    app.dependency_overrides[get_chatbot_dep] = lambda: model
    yield model
    app.dependency_overrides.pop(get_chatbot_dep, None)


async def _ids(team) -> dict:
    async with as_user(team["prof"]) as prof:
        batch = await _batch(prof, await _three_groups(prof, team["reading"]))
    return {mode: _first(batch, mode)["code"] for mode in ("seei", "chatbot", "reading_only")} | {
        "batch": batch["id"]
    }


async def _rows(url: str, model, code: str):
    engine = create_async_engine(url)
    maker = async_sessionmaker(engine)
    async with maker() as s:
        rows = list(
            await s.scalars(
                select(model)
                .join(Participant, Participant.id == model.participant_id)
                .where(Participant.code == code)
                .order_by(model.created_at if model is ChatMessage else model.at)
            )
        )
    await engine.dispose()
    return rows


async def _say(client, text):
    r = await client.post("/trial/chat", json={"text": text})
    assert r.status_code == 200
    return parse_sse(r.text)


# --------------------------------------------------------------------------- #
# the chatbot


@pytest.mark.anyio
async def test_the_chatbot_is_a_conversation_with_no_reading_and_no_prompt(team, chatbot, trial_on):
    ids = await _ids(team)
    async with as_participant(ids["chatbot"]) as me:
        await me.post("/trial/clock")
        first = await _say(me, "What is offloading?")
        second = await _say(me, "  An example?  ")
        history = (await me.get("/trial/chat")).json()

    kinds = [k for k, _ in first]
    assert kinds[0] == "message_start" and kinds[-1] == "message_end" and "delta" in kinds
    assert "message 2 of the conversation" in dict(second)["message_end"]["content"]
    # The model saw the conversation and nothing else: no reading, no instructions.
    assert chatbot.sent[-1][0] == ("user", "What is offloading?")
    assert chatbot.sent[-1][-1] == ("user", "An example?")
    assert [r for r, _ in chatbot.sent[-1]] == ["user", "assistant", "user"]
    assert [(m["role"], m["content"][:11]) for m in history] == [
        ("user", "What is off"),
        ("assistant", "[MOCK chatb"),
        ("user", "An example?"),
        ("assistant", "[MOCK chatb"),
    ]


@pytest.mark.anyio
async def test_only_the_chatbot_group_can_chat_and_only_once_the_reading_opens(team, chatbot):
    ids = await _ids(team)
    async with as_participant(ids["chatbot"]) as me:
        assert await _say(me, "hi") == [("error", {"detail": "the reading has not opened"})]
    for mode in ("seei", "reading_only"):
        async with as_participant(ids[mode]) as me:
            await me.post("/trial/clock")
            assert await _say(me, "hi") == [
                ("error", {"detail": "this class does not use the chatbot"})
            ]


@pytest.mark.anyio
async def test_a_failed_reply_keeps_the_question_and_logs_the_failure(team, trial_on):
    from backend.deps import get_chatbot_dep
    from backend.main import app

    ids = await _ids(team)
    app.dependency_overrides[get_chatbot_dep] = lambda: Broken()
    async with as_participant(ids["chatbot"]) as me:
        await me.post("/trial/clock")
        events = await _say(me, "Will this work?")

    assert events[-1] == ("error", {"detail": "chatbot failed: RuntimeError"})
    messages = await _rows(trial_on, ChatMessage, ids["chatbot"])
    assert [(m.role, m.content) for m in messages] == [("user", "Will this work?")]
    logged = await _rows(trial_on, TrialEvent, ids["chatbot"])
    assert [(e.kind, e.data) for e in logged][-1] == ("turn_failed", {"where": "chatbot"})


# --------------------------------------------------------------------------- #
# Done


@pytest.mark.anyio
async def test_done_ends_a_control_group_and_counts_as_finished(team, chatbot):
    ids = await _ids(team)
    async with as_participant(ids["reading_only"]) as me:
        assert (await me.post("/trial/done")).status_code == 409  # reading not open
        await me.post("/trial/clock")
        done = (await me.post("/trial/done")).json()
        again = (await me.post("/trial/done")).json()
    assert done["done"] is True and again["done"] is True

    async with as_participant(ids["chatbot"]) as me:
        await me.post("/trial/clock")
        await me.post("/trial/done")
        assert await _say(me, "one more?") == [("error", {"detail": "you are done"})]

    async with as_participant(ids["seei"]) as me:
        await me.post("/trial/clock")
        assert (await me.post("/trial/done")).status_code == 409

    async with as_user(team["prof"]) as prof:
        batch = (await prof.get(f"/instructor/batches/{ids['batch']}")).json()
    status = {p["code"]: p["status"] for p in batch["participants"]}
    assert status[ids["reading_only"]] == "finished"
    assert status[ids["chatbot"]] == "finished"
    assert status[ids["seei"]] == "signed_in"


@pytest.mark.anyio
async def test_done_after_time_is_up_records_nothing(team, chatbot, trial_on):
    ids = await _ids(team)
    async with as_participant(ids["reading_only"]) as me:
        await me.post("/trial/clock")
        await _set_clock(trial_on, ids["reading_only"], minutes_ago=41)
        status = (await me.post("/trial/done")).json()
    assert (status["done"], status["time_up"]) == (False, True)

    async with as_participant(ids["chatbot"]) as me:
        await me.post("/trial/clock")
        await _set_clock(trial_on, ids["chatbot"], minutes_ago=41)
        assert await _say(me, "late?") == [("error", {"detail": "time is up"})]

    async with as_user(team["prof"]) as prof:
        batch = (await prof.get(f"/instructor/batches/{ids['batch']}")).json()
    status = {p["code"]: p["status"] for p in batch["participants"]}
    assert status[ids["reading_only"]] == "finished"  # by time


# --------------------------------------------------------------------------- #
# the event log


@pytest.mark.anyio
async def test_the_event_log_keeps_known_events_in_the_order_they_happened(team, chatbot, trial_on):
    ids = await _ids(team)
    now = utcnow()
    sent = [
        {"kind": "panel_opened", "at": (now + timedelta(seconds=2)).isoformat(), "data": {"panel": "rubric"}},
        {"kind": "paste", "at": (now + timedelta(seconds=3)).isoformat(), "data": {"length": 412}},
        {"kind": "keylogger", "at": now.isoformat(), "data": {"keys": "secret"}},
        {"kind": "tab_left", "at": (now - timedelta(days=3)).isoformat()},
    ]
    async with as_participant(ids["reading_only"]) as me:
        await me.post("/trial/clock")
        r = await me.post("/trial/events", json={"events": sent})
        assert r.status_code == 204
        await me.post("/trial/done")

    logged = await _rows(trial_on, TrialEvent, ids["reading_only"])
    kinds = [e.kind for e in logged]
    # Unknown kinds are dropped; the server adds what only it knows.
    assert "keylogger" not in kinds
    assert set(kinds) == {"reading_opened", "panel_opened", "paste", "tab_left", "done"}
    assert kinds[0] == "reading_opened"
    paste = next(e for e in logged if e.kind == "paste")
    assert paste.data == {"length": 412}
    # A browser clock three days out is not believed.
    tab = next(e for e in logged if e.kind == "tab_left")
    assert abs(tab.at - tab.received_at) < timedelta(minutes=1)


@pytest.mark.anyio
async def test_only_a_participant_has_an_event_log(team):
    async with as_user(team["prof"]) as prof:
        r = await prof.post("/trial/events", json={"events": []})
    assert r.status_code == 403
