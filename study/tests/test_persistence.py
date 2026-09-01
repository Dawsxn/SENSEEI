"""Persistence: does a participant survive the process dying?

The question these tests answer is narrow and total. A single-sitting trial gets
one afternoon; if a restart loses what was collected, there is no second run. So
the central test is not that rows exist — it is that a participant walked most of
the way through, in one arm, comes back *identical*.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from study.api.app import create_app
from study.api.store import TrialStore
from study.arms import Arm
from study.interventions.unguided import OfflineChatBackend
from study.persistence import IdentityRow, ParticipantRow, Repository
from study.phases import Phase, utcnow
from study.trial_config import load_trial_config


@pytest.fixture
def url(tmp_path):
    return f"sqlite:///{tmp_path / 'trial.db'}"


@pytest.fixture
def config():
    return load_trial_config("study/trial.yaml")


def make_store(config, url) -> TrialStore:
    return TrialStore(
        config, chat_backend=OfflineChatBackend(), repository=Repository(url)
    )


def make_client(config, store) -> TestClient:
    return TestClient(create_app(config=config, store=store))


def walk_to_intervention(client, code):
    client.post(f"/p/{code}/submit", data={
        "item_year_level": "3",
        "item_department": "Management and Organization",
        "item_prior_course": "no",
    })
    client.post(f"/p/{code}/advance")  # pre-test is a stub
    return client.app.state.store.by_code(code)


def check_in_arm(client, arm: Arm) -> str:
    for _ in range(9):
        client.post("/check-in", data={"name": "Test Person", "consent_form_serial": "CF-1"})
        participant = client.app.state.store.all()[-1]
        if participant.arm is arm:
            return participant.access_code
    raise AssertionError(f"No participant assigned to {arm}")


# --- durability -----------------------------------------------------------


def test_a_store_without_a_repository_says_it_is_not_durable(config):
    assert not TrialStore(config).is_durable


def test_a_store_with_a_repository_is_durable(config, url):
    assert make_store(config, url).is_durable


def test_the_console_stops_warning_once_records_are_durable(config, url):
    client = make_client(config, make_store(config, url))
    assert "held in memory only" not in client.get("/").text


# --- the round trip -------------------------------------------------------


def test_a_participant_survives_a_restart(config, url):
    client = make_client(config, make_store(config, url))
    client.post("/check-in", data={"name": "Alma R.", "consent_form_serial": "CF-9"})
    original = client.app.state.store.all()[0]

    revived = make_store(config, url)
    revived.reload()
    restored = revived.get(original.participant_id)

    assert restored is not None
    assert restored.arm is original.arm
    assert restored.access_code == original.access_code


def test_their_access_code_still_works_after_a_restart(config, url):
    client = make_client(config, make_store(config, url))
    code = check_in_arm(client, Arm.PASSIVE)

    revived = make_store(config, url)
    revived.reload()

    assert revived.by_code(code) is not None


def test_a_walked_through_participant_comes_back_identical(config, url):
    """The one that matters. Phase, history, and the intervention clock."""
    client = make_client(config, make_store(config, url))
    code = check_in_arm(client, Arm.PASSIVE)
    original = walk_to_intervention(client, code)

    revived = make_store(config, url)
    revived.reload()
    restored = revived.by_code(code)

    assert restored.state.phase is original.state.phase
    assert restored.state.entered_at == original.state.entered_at
    assert restored.state.intervention_started_at == original.state.intervention_started_at
    assert len(restored.state.history) == len(original.state.history)


def test_the_intervention_clock_keeps_running_across_a_restart(config, url):
    """A restart must not hand anyone a fresh forty minutes."""
    client = make_client(config, make_store(config, url))
    code = check_in_arm(client, Arm.PASSIVE)
    walk_to_intervention(client, code)

    revived = make_store(config, url)
    revived.reload()
    restored = revived.by_code(code)

    from study.phases import deadline

    assert deadline(restored.state, config.timing) is not None
    assert restored.state.intervention_started_at < utcnow() + timedelta(seconds=1)


def test_a_chat_transcript_survives(config, url):
    client = make_client(config, make_store(config, url))
    code = check_in_arm(client, Arm.UNGUIDED_LLM)
    walk_to_intervention(client, code)
    client.post(f"/p/{code}/chat", data={"message": "what is a switching cost"})

    revived = make_store(config, url)
    revived.reload()
    telemetry = revived.by_code(code).unguided.telemetry()

    assert telemetry.turn_count == 1
    assert telemetry.word_count == 5


def test_the_participant_can_carry_on_chatting_after_a_restart(config, url):
    client = make_client(config, make_store(config, url))
    code = check_in_arm(client, Arm.UNGUIDED_LLM)
    walk_to_intervention(client, code)
    client.post(f"/p/{code}/chat", data={"message": "first question here"})

    revived = make_store(config, url)
    revived.reload()
    resumed = make_client(config, revived)
    resumed.post(f"/p/{code}/chat", data={"message": "second question"})

    assert revived.by_code(code).unguided.telemetry().turn_count == 2


def test_reading_telemetry_survives(config, url):
    client = make_client(config, make_store(config, url))
    code = check_in_arm(client, Arm.PASSIVE)
    walk_to_intervention(client, code)
    client.post(f"/p/{code}/reading-event", data={"kind": "scroll", "depth": 0.8})
    client.post(f"/p/{code}/reading-event", data={"kind": "away"})

    revived = make_store(config, url)
    revived.reload()
    telemetry = revived.by_code(code).passive.telemetry()

    assert telemetry.max_scroll_depth == pytest.approx(0.8)
    assert telemetry.away_count == 1


def test_instrument_answers_survive(config, url):
    client = make_client(config, make_store(config, url))
    client.post("/check-in", data={"name": "Ben T.", "consent_form_serial": "CF-2"})
    code = client.app.state.store.all()[0].access_code
    client.post(f"/p/{code}/submit", data={
        "item_year_level": "4",
        "item_department": "MOD",
        "item_prior_course": "unsure",
    })

    revived = make_store(config, url)
    revived.reload()
    result = revived.by_code(code).responses[Phase.DEMOGRAPHICS]

    assert result.answers["prior_course"] == "unsure"
    assert result.screening == {"prior_course": "unsure"}


def test_incidents_survive(config, url):
    client = make_client(config, make_store(config, url))
    client.post("/check-in", data={"name": "Cai L."})
    participant_id = client.app.state.store.all()[0].participant_id
    client.post(f"/participants/{participant_id}/incident",
                data={"note": "browser crashed at 12 min"})

    revived = make_store(config, url)
    revived.reload()

    assert len(revived.get(participant_id).incidents) == 1


def test_the_allocation_is_not_re_drawn_on_reload(config, url):
    """A restart must not reassign anyone to a different arm."""
    client = make_client(config, make_store(config, url))
    for _ in range(6):
        client.post("/check-in", data={"name": "x"})
    before = {p.participant_id: p.arm for p in client.app.state.store.all()}

    revived = make_store(config, url)
    revived.reload()

    assert {p.participant_id: p.arm for p in revived.all()} == before


def test_check_in_continues_from_where_it_left_off(config, url):
    """The next participant after a restart is the next one, not the first."""
    client = make_client(config, make_store(config, url))
    for _ in range(3):
        client.post("/check-in", data={"name": "x"})

    revived = make_store(config, url)
    revived.reload()
    following = revived.check_in(utcnow(), name="fourth")

    assert following.participant_id == "P-004"


# --- identity held separately (§4.7.4) ------------------------------------


def test_identity_lives_in_its_own_table(config, url):
    """§4.7.4: identifiers handled separately from research data."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    client = make_client(config, make_store(config, url))
    client.post("/check-in", data={"name": "Alma R.", "consent_form_serial": "CF-9"})
    repository = client.app.state.store.repository

    with Session(repository.engine) as db:
        research = db.scalars(select(ParticipantRow)).all()
        identities = db.scalars(select(IdentityRow)).all()

    assert identities[0].name == "Alma R."
    assert "Alma" not in research[0].snapshot


def test_the_research_row_carries_no_name(config, url):
    """Pseudonymisation is a property of the schema, not of the export code."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    client = make_client(config, make_store(config, url))
    client.post("/check-in", data={"name": "Distinctive Name", "consent_form_serial": "CF-1"})
    repository = client.app.state.store.repository

    with Session(repository.engine) as db:
        row = db.scalars(select(ParticipantRow)).first()

    assert "Distinctive Name" not in row.snapshot
    assert row.participant_id


def test_a_name_comes_back_on_reload(config, url):
    """It is held apart, not thrown away — a withdrawal has to find them."""
    client = make_client(config, make_store(config, url))
    client.post("/check-in", data={"name": "Alma R.", "consent_form_serial": "CF-9"})

    revived = make_store(config, url)
    revived.reload()

    assert revived.all()[0].name == "Alma R."


# --- withdrawal (§4.7.1) --------------------------------------------------


def test_withdrawing_removes_both_the_record_and_the_identity(config, url):
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    client = make_client(config, make_store(config, url))
    client.post("/check-in", data={"name": "Alma R.", "consent_form_serial": "CF-9"})
    store = client.app.state.store
    participant_id = store.all()[0].participant_id

    client.post(f"/participants/{participant_id}/withdraw")

    with Session(store.repository.engine) as db:
        assert db.scalars(select(ParticipantRow)).all() == []
        assert db.scalars(select(IdentityRow)).all() == []


def test_a_withdrawal_does_not_come_back_on_reload(config, url):
    client = make_client(config, make_store(config, url))
    client.post("/check-in", data={"name": "Alma R."})
    participant_id = client.app.state.store.all()[0].participant_id
    client.post(f"/participants/{participant_id}/withdraw")

    revived = make_store(config, url)
    revived.reload()

    assert revived.get(participant_id) is None


def test_withdrawing_an_unknown_participant_is_a_404(config, url):
    client = make_client(config, make_store(config, url))
    assert client.post("/participants/P-999/withdraw").status_code == 404


def test_end_of_retention_deletion_clears_everything(config, url):
    """§4.6.6: data deleted at the end of the retention period."""
    client = make_client(config, make_store(config, url))
    for _ in range(3):
        client.post("/check-in", data={"name": "x"})
    repository = client.app.state.store.repository

    repository.delete_everything()

    assert repository.count() == 0


# --- restoring without a chat backend -------------------------------------


def test_a_transcript_is_not_lost_when_no_backend_is_configured(config, url):
    """Reloading without a model must not silently drop a session's data.

    The session cannot be resumed — there is nothing to answer with — but the
    transcript is research data and stays in the database either way.
    """
    client = make_client(config, make_store(config, url))
    code = check_in_arm(client, Arm.UNGUIDED_LLM)
    walk_to_intervention(client, code)
    client.post(f"/p/{code}/chat", data={"message": "a question"})
    participant_id = client.app.state.store.by_code(code).participant_id

    revived = TrialStore(config, chat_backend=None, repository=Repository(url))
    revived.reload()

    assert revived.get(participant_id) is not None
    assert revived.get(participant_id).unguided is None  # cannot resume

    with_backend = make_store(config, url)
    with_backend.reload()
    assert with_backend.get(participant_id).unguided.telemetry().turn_count == 1
