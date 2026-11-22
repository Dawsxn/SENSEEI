"""What changed for the trial sittings: the team shares the trial's classes,
readings and batches; a batch exports on its own; the provider settings can send
the figures to a different provider; the OpenAI-compatible provider streams;
and a provider's error reaches the log without any key in it."""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from types import SimpleNamespace

import pytest

from test_trial_api import (  # noqa: F401  (fixtures are used by name)
    _batch,
    _clear_overrides,
    _three_groups,
    as_user,
    team,
    trial_on,
)


def _codes(zip_bytes: bytes) -> set[str]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        text = zf.read("participants.csv").decode("utf-8-sig")
    return {row["participant_id"] for row in csv.DictReader(io.StringIO(text))}


# --------------------------------------------------------------------------- #
# the team shares the trial


@pytest.mark.anyio
@pytest.mark.usefixtures("fresh_engine")
async def test_every_team_account_sees_and_runs_the_trial(team):
    async with as_user(team["prof"]) as prof:
        classes = await _three_groups(prof, team["reading"])
        batch = await _batch(prof, classes, per_class=1)

    async with as_user(team["other"]) as other:
        assert {c["id"] for c in (await other.get("/instructor/classes")).json()} == set(
            classes.values()
        )
        assert [r["id"] for r in (await other.get("/instructor/readings")).json()] == [
            str(team["reading"])
        ]
        assert [b["id"] for b in (await other.get("/instructor/batches")).json()] == [batch["id"]]
        # and can act on it, not just look
        r = await other.post(f"/instructor/batches/{batch['id']}/close")
        assert r.status_code == 200, r.text


@pytest.mark.anyio
@pytest.mark.usefixtures("fresh_engine")
async def test_a_batch_exports_only_its_own_ids(team):
    async with as_user(team["prof"]) as prof:
        classes = await _three_groups(prof, team["reading"])
        first = await _batch(prof, classes, per_class=1)
        second = await _batch(prof, classes, per_class=1)

        r = await prof.get(f"/instructor/batches/{first['id']}/export")
        assert r.status_code == 200, r.text
        assert "sitting-1" in r.headers["content-disposition"]
        assert _codes(r.content) == {p["code"] for p in first["participants"]}

        everything = _codes((await prof.get("/instructor/export")).content)
        assert everything == {p["code"] for b in (first, second) for p in b["participants"]}

        missing = "00000000-0000-0000-0000-000000000000"
        assert (await prof.get(f"/instructor/batches/{missing}/export")).status_code == 404


# --------------------------------------------------------------------------- #
# provider settings


def test_figures_use_the_main_provider_unless_told_otherwise(monkeypatch):
    from backend.settings import Settings

    for k in ("FIGURE_PROVIDER", "FIGURE_MODEL", "FIGURE_API_KEY_ENV", "FIGURE_BASE_URL"):
        monkeypatch.delenv(k, raising=False)
    deepseek = dict(
        llm_provider="openai_compat",
        llm_model="deepseek-flash",
        llm_api_key_env="DEEPSEEK_API_KEY",
        llm_base_url="https://api.deepseek.com",
        _env_file=None,
    )
    s = Settings(**deepseek)
    assert s.provider_config()["base_url"] == "https://api.deepseek.com"
    assert s.figure_provider_config() == s.provider_config()

    s = Settings(
        **deepseek,
        figure_provider="gemini",
        figure_model="gemini-3.1-pro-preview",
        figure_api_key_env="GEMINI_API_KEY",
    )
    fig = s.figure_provider_config()
    assert (fig["provider"], fig["model"], fig["api_key_env"], fig["base_url"]) == (
        "gemini", "gemini-3.1-pro-preview", "GEMINI_API_KEY", None,
    )
    assert s.provider_config()["provider"] == "openai_compat"  # the agents are untouched


def _chunk(text=None, finish=None, usage=None):
    choices = [] if text is None and finish is None else [
        SimpleNamespace(delta=SimpleNamespace(content=text), finish_reason=finish)
    ]
    return SimpleNamespace(choices=choices, usage=usage)


def test_the_openai_compatible_provider_streams_and_keeps_usage(monkeypatch):
    from agents.providers.openai_compat import OpenAICompatProvider

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    p = OpenAICompatProvider(
        {"model": "deepseek-flash", "api_key_env": "DEEPSEEK_API_KEY",
         "base_url": "https://api.deepseek.com", "json_mode": False}
    )
    sent = {}

    def create(**kwargs):
        sent.update(kwargs)
        return iter([
            _chunk("Hel"), _chunk("lo"), _chunk(finish="stop"),
            _chunk(usage=SimpleNamespace(prompt_tokens=5, completion_tokens=2, total_tokens=7)),
        ])

    p.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    assert list(p.stream("sys", "hi")) == ["Hel", "lo"]
    assert sent["stream"] is True and "response_format" not in sent
    assert sent["messages"][0] == {"role": "system", "content": "sys"}
    assert p.last_finish_reason == "stop"
    assert p.last_usage["total_tokens"] == 7

    assert "".join(p.chat_stream([("user", "a"), ("assistant", "b"), ("user", "c")])) == "Hello"
    assert [m["role"] for m in sent["messages"]] == ["user", "assistant", "user"]


def test_the_openai_compatible_provider_searches_the_web_when_asked(monkeypatch):
    from agents.providers.openai_compat import OpenAICompatProvider

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    p = OpenAICompatProvider(
        {"model": "deepseek-flash", "api_key_env": "DEEPSEEK_API_KEY",
         "base_url": "https://api.deepseek.com", "json_mode": False}
    )
    sent = {}
    calls = [{"type": "deepseek_web_search", "query": "strategic offensive"}]
    cites = [{"type": "url_citation", "url_citation": {"url": "https://a.example", "title": "A"}}]

    def create(**kwargs):
        sent.update(kwargs)
        last = SimpleNamespace(
            choices=[SimpleNamespace(
                delta=SimpleNamespace(content=None, server_tool_calls=calls, annotations=cites),
                finish_reason="stop",
            )],
            usage=None,
        )
        return iter([_chunk("An offensive"), _chunk(" is…"), last])

    p.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    found = {}
    turns = [("user", "a"), ("assistant", "b", {"server_tool_calls": [{"q": 1}]}), ("user", "c")]
    assert "".join(p.chat_stream(turns, "sys", web_search=True, found=found)) == "An offensive is…"
    assert sent["tools"] == [{"type": "deepseek_web_search"}]
    assert sent["messages"][2] == {"role": "assistant", "content": "b", "server_tool_calls": [{"q": 1}]}
    assert found == {"server_tool_calls": calls, "annotations": cites}

    # Off: no tool, and an earlier record is not sent.
    found = {}
    sent.clear()
    list(p.chat_stream(turns, "sys", found=found))
    assert "tools" not in sent and "server_tool_calls" not in sent["messages"][2]


def test_a_provider_error_is_logged_without_the_key(monkeypatch, caplog):
    from backend.services.provider_errors import log_failure

    monkeypatch.setenv("DEEPSEEK_API_KEY", "dsk-secret-value-123")
    with caplog.at_level(logging.ERROR, logger="senseei.provider"):
        log_failure("tutor", RuntimeError(
            "401 your key dsk-secret-value-123 is invalid; also AIzaSyA1234567890abcdefghijklmnop"
        ))
    line = caplog.records[-1].getMessage()
    assert "tutor" in line and "RuntimeError: 401" in line
    assert "dsk-secret-value-123" not in line and "AIzaSy" not in line


# --------------------------------------------------------------------------- #
# one reading per class on the trial site


@pytest.mark.anyio
@pytest.mark.usefixtures("fresh_engine")
async def test_a_trial_class_takes_only_one_reading(team, trial_on):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from backend.models import Reading

    async with as_user(team["prof"]) as prof:
        classes = await _three_groups(prof, team["reading"])  # gives each the reading

        engine = create_async_engine(trial_on)
        async with async_sessionmaker(engine)() as s:
            second = Reading(uploaded_by=team["prof"], title="Another", content="body")
            s.add(second)
            second_id = str(second.id)  # set on creation; read it before the commit expires it
            await s.commit()
        await engine.dispose()

        r = await prof.put(
            f"/instructor/readings/{second_id}/classes",
            json={"class_ids": [classes["seei"]]},
        )
        assert r.status_code == 409 and r.json()["detail"] == "class_has_reading"

        # the reading a class already has can be saved again, and taken off
        r = await prof.put(
            f"/instructor/readings/{team['reading']}/classes",
            json={"class_ids": [classes["seei"], classes["chatbot"]]},
        )
        assert r.status_code == 200, r.text
        # with reading_only now free, the second reading may go there
        r = await prof.put(
            f"/instructor/readings/{second_id}/classes",
            json={"class_ids": [classes["reading_only"]]},
        )
        assert r.status_code == 200, r.text
