"""The trial's export, and withdrawing a participant (docs/context/trial.md).

One small sitting is played through all three groups, then exported. The
export must hold every participant's record under their ID and nothing that
says who they are; withdrawing an ID must take all of it away.
"""

from __future__ import annotations

import csv
import io
import zipfile

import pytest

from test_session_api import parse_sse
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
from test_trial_groups_api import chatbot  # noqa: F401

pytestmark = pytest.mark.usefixtures("fresh_engine")

FILES = {
    "README.txt", "participants.csv", "sessions.csv", "attempts.csv", "criteria.csv",
    "tutor_messages.csv", "chat_messages.csv", "events.csv",
}


def _read(zip_bytes: bytes) -> dict[str, list[dict]]:
    out = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        assert set(zf.namelist()) == FILES
        for name in zf.namelist():
            if name.endswith(".csv"):
                text = zf.read(name).decode("utf-8-sig")
                out[name] = list(csv.DictReader(io.StringIO(text)))
    return out


async def _sitting(team) -> dict:
    """One ID per group, each having done its part."""
    from agents.rubric import load_rubric

    load_rubric("agents/rubrics/rubric_v3.yaml")  # the stub grader judges by it
    async with as_user(team["prof"]) as prof:
        batch = await _batch(prof, await _three_groups(prof, team["reading"]), per_class=1)
    ids = {m: _first(batch, m)["code"] for m in ("seei", "chatbot", "reading_only")}

    async with as_participant(ids["seei"]) as me:
        await me.post("/trial/clock")
        start = await me.post("/sessions", json={"reading_id": str(team["reading"])})
        session_id = dict(parse_sse(start.text))["session"]["id"]
        await me.post(f"/sessions/{session_id}/responses", json={"text": "my statement"})
        await me.post("/trial/events", json={"events": [
            {"kind": "panel_opened", "at": "2026-10-28T01:00:00+00:00", "data": {"panel": "rubric"}},
        ]})
    async with as_participant(ids["chatbot"]) as me:
        await me.post("/trial/clock")
        await me.post("/trial/chat", json={"text": "what is it?"})
    async with as_participant(ids["reading_only"]) as me:
        await me.post("/trial/clock")
        await me.post("/trial/done")
    return ids


@pytest.mark.anyio
async def test_the_export_holds_everyone_by_id_and_no_one_by_name(team, chatbot):
    ids = await _sitting(team)
    async with as_user(team["prof"]) as prof:
        r = await prof.get("/instructor/export")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert "senseei-trial-" in r.headers["content-disposition"]
    data = _read(r.content)

    people = {row["participant_id"]: row for row in data["participants.csv"]}
    assert set(people) == set(ids.values())
    assert people[ids["reading_only"]]["done_at"]
    assert people[ids["chatbot"]]["group"] == "chatbot"
    assert all(row["reading_opened_at"] and row["time_ran_out_at"] for row in people.values())

    assert [r["participant_id"] for r in data["sessions.csv"]] == [ids["seei"]]
    attempt = data["attempts.csv"][0]
    assert (attempt["participant_id"], attempt["response_text"], attempt["verdict"]) == (
        ids["seei"], "my statement", "PASS",
    )
    assert data["criteria.csv"] and data["tutor_messages.csv"]
    assert [(m["participant_id"], m["role"]) for m in data["chat_messages.csv"]] == [
        (ids["chatbot"], "user"), (ids["chatbot"], "assistant"),
    ]
    kinds = {(e["participant_id"], e["kind"]) for e in data["events.csv"]}
    assert (ids["seei"], "panel_opened") in kinds and (ids["reading_only"], "done") in kinds

    # No column anywhere carries an email or a name other than the ID.
    for rows in data.values():
        for row in rows:
            assert not any("@" in str(v) for v in row.values())
            assert "email" not in row and "name" not in row


@pytest.mark.anyio
async def test_withdrawing_an_id_deletes_everything_under_it(team, chatbot):
    ids = await _sitting(team)
    async with as_user(team["prof"]) as prof:
        assert (await prof.delete(f"/instructor/participants/{ids['seei'].lower()}")).status_code == 204
        assert (await prof.delete(f"/instructor/participants/{ids['seei']}")).status_code == 404
        data = _read((await prof.get("/instructor/export")).content)

    for name, rows in data.items():
        assert ids["seei"] not in {r["participant_id"] for r in rows}, name
    assert data["sessions.csv"] == [] and data["attempts.csv"] == [] and data["criteria.csv"] == []
    assert {r["participant_id"] for r in data["participants.csv"]} == {
        ids["chatbot"], ids["reading_only"],
    }
    from test_trial_api import _client

    async with _client() as anyone:
        r = await anyone.post("/auth/participant", json={"code": ids["seei"]})
    assert r.status_code == 404


@pytest.mark.anyio
async def test_only_the_team_exports_or_withdraws_and_only_in_trial_mode(team, monkeypatch):
    from backend.settings import get_settings

    async with as_user(team["prof"]) as prof:
        batch = await _batch(prof, await _three_groups(prof, team["reading"]), per_class=1)
    code = _first(batch, "seei")["code"]
    async with as_participant(code) as me:
        assert (await me.get("/instructor/export")).status_code == 403
        assert (await me.delete(f"/instructor/participants/{code}")).status_code == 403

    monkeypatch.setenv("TRIAL_MODE", "false")
    get_settings.cache_clear()
    async with as_user(team["prof"]) as prof:
        assert (await prof.get("/instructor/export")).status_code == 404
        assert (await prof.delete(f"/instructor/participants/{code}")).status_code == 404
