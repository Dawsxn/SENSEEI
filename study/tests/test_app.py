"""The running trial, end to end: check-in, the three arms, and the gate.

The gate tests here matter more than the ones in test_phases.py. Those check the
rule; these check that no route around the outside of it exists — a hand-typed
URL, a resubmitted form, a participant who simply keeps clicking.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from study.arms import Arm
from study.interventions.unguided import OfflineChatBackend
from study.phases import Phase
from study.api.app import create_app
from study.api.store import TrialStore
from study.trial_config import load_trial_config


@pytest.fixture
def client():
    config = load_trial_config("study/trial.yaml")
    store = TrialStore(config, chat_backend=OfflineChatBackend())
    return TestClient(create_app(config=config, store=store))


def check_in(client, name="Test Person") -> tuple[str, str]:
    """Check someone in; return their participant id and access code."""
    client.post("/check-in", data={"name": name, "consent_form_serial": "CF-1"})
    store = client.app.state.store
    participant = store.all()[-1]
    return participant.participant_id, participant.access_code


def check_in_arm(client, arm: Arm) -> str:
    """Check people in until one lands in ``arm``; return their access code."""
    for _ in range(9):
        _, code = check_in(client)
        if client.app.state.store.by_code(code).arm is arm:
            return code
    raise AssertionError(f"No participant assigned to {arm} within one block")


# --- the console ----------------------------------------------------------


def test_the_console_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Proctor console" in response.text


def test_the_console_warns_that_records_are_not_durable(client):
    """A restart mid-sitting would lose 45 people with no way to redo it."""
    assert "held in memory only" in client.get("/").text


def test_check_in_assigns_from_the_allocation_not_by_choice(client):
    store = client.app.state.store
    codes = [check_in(client)[1] for _ in range(9)]
    arms = [store.by_code(c).arm for c in codes]

    assert sorted(arms, key=lambda a: a.value) == sorted(
        [Arm.SENSEEI] * 3 + [Arm.UNGUIDED_LLM] * 3 + [Arm.PASSIVE] * 3,
        key=lambda a: a.value,
    )


def test_participants_are_numbered_in_check_in_order(client):
    assert [check_in(client)[0] for _ in range(3)] == ["P-001", "P-002", "P-003"]


def test_access_codes_are_unguessable_and_unique(client):
    codes = {check_in(client)[1] for _ in range(5)}
    assert len(codes) == 5
    assert all(len(c) >= 8 for c in codes)


def test_an_unknown_code_is_not_a_session(client):
    assert client.get("/p/nonsense").status_code == 404


def test_check_in_stops_when_the_allocation_runs_out(client):
    for _ in range(45):
        check_in(client)
    assert client.post("/check-in", data={"name": "one too many"}).status_code == 409


# --- the gate, from the outside -------------------------------------------


def advance_to_intervention(client, code):
    client.post(f"/p/{code}/advance")  # demographics -> pre-test
    client.post(f"/p/{code}/advance")  # pre-test -> intervention
    return client.app.state.store.by_code(code)


def test_a_participant_cannot_click_past_the_gate(client):
    _, code = check_in(client)
    participant = advance_to_intervention(client, code)

    for _ in range(5):
        client.post(f"/p/{code}/advance")

    assert participant.state.phase is Phase.INTERVENTION


def test_a_held_participant_cannot_click_past_the_gate_either(client):
    _, code = check_in(client)
    participant = advance_to_intervention(client, code)
    client.post(f"/p/{code}/finished-early")

    client.post(f"/p/{code}/advance")

    assert participant.state.phase is Phase.HOLD


def test_finishing_early_does_not_shorten_the_clock(client):
    _, code = check_in(client)
    participant = advance_to_intervention(client, code)
    started = participant.state.intervention_started_at

    client.post(f"/p/{code}/finished-early")

    assert participant.state.intervention_started_at == started


def test_the_hold_screen_says_why_they_are_waiting(client):
    _, code = check_in(client)
    advance_to_intervention(client, code)
    client.post(f"/p/{code}/finished-early")

    assert "same amount of time" in client.get(f"/p/{code}").text


def test_a_proctor_can_release_someone_and_it_is_recorded(client):
    participant_id, code = check_in(client)
    participant = advance_to_intervention(client, code)

    client.post(f"/participants/{participant_id}/release")

    assert participant.state.phase is Phase.POST_TEST_A
    assert any(visit.forced for visit in participant.state.history)


# --- the unguided arm -----------------------------------------------------


def test_the_chat_records_both_sides(client):
    code = check_in_arm(client, Arm.UNGUIDED_LLM)
    participant = advance_to_intervention(client, code)

    client.post(f"/p/{code}/chat", data={"message": "what is a switching cost"})

    assert participant.unguided.telemetry().turn_count == 1
    assert len(participant.unguided.conversation.turns) == 2


def test_the_chat_page_shows_the_conversation(client):
    code = check_in_arm(client, Arm.UNGUIDED_LLM)
    advance_to_intervention(client, code)
    client.post(f"/p/{code}/chat", data={"message": "hello there"})

    assert "hello there" in client.get(f"/p/{code}").text


def test_the_chat_page_carries_no_instruction_about_how_to_study(client):
    """§4.6.2: no pedagogical framing. Naming SEE-I here would be scaffolding."""
    code = check_in_arm(client, Arm.UNGUIDED_LLM)
    advance_to_intervention(client, code)
    page = client.get(f"/p/{code}").text.lower()

    for word in ("see-i", "state", "elaborate", "exemplify", "illustrate"):
        assert word not in page


def test_an_empty_message_is_not_recorded(client):
    code = check_in_arm(client, Arm.UNGUIDED_LLM)
    participant = advance_to_intervention(client, code)

    client.post(f"/p/{code}/chat", data={"message": "   "})

    assert participant.unguided.telemetry().turn_count == 0


def test_the_chat_is_closed_to_other_arms(client):
    code = check_in_arm(client, Arm.PASSIVE)
    advance_to_intervention(client, code)

    response = client.post(f"/p/{code}/chat", data={"message": "hello"})
    assert response.status_code == 403


def test_the_chat_is_closed_outside_the_intervention(client):
    code = check_in_arm(client, Arm.UNGUIDED_LLM)
    response = client.post(f"/p/{code}/chat", data={"message": "hello"})
    assert response.status_code == 409


# --- the passive arm ------------------------------------------------------


def test_the_reader_records_time_away_from_the_text(client):
    code = check_in_arm(client, Arm.PASSIVE)
    participant = advance_to_intervention(client, code)

    client.post(f"/p/{code}/reading-event", data={"kind": "away"})
    client.post(f"/p/{code}/reading-event", data={"kind": "back"})

    assert participant.passive.telemetry().away_count == 1


def test_the_reader_records_scroll_depth(client):
    code = check_in_arm(client, Arm.PASSIVE)
    participant = advance_to_intervention(client, code)

    client.post(f"/p/{code}/reading-event", data={"kind": "scroll", "depth": 0.75})

    assert participant.passive.telemetry().max_scroll_depth == pytest.approx(0.75)


def test_an_out_of_range_scroll_depth_is_clamped_not_rejected(client):
    """A browser can report an odd value; it must not break the session."""
    code = check_in_arm(client, Arm.PASSIVE)
    participant = advance_to_intervention(client, code)

    client.post(f"/p/{code}/reading-event", data={"kind": "scroll", "depth": 9.9})

    assert participant.passive.telemetry().max_scroll_depth == 1.0


def test_the_reading_is_served_to_the_passive_arm(client):
    code = check_in_arm(client, Arm.PASSIVE)
    advance_to_intervention(client, code)

    assert "switching cost" in client.get(f"/p/{code}").text.lower()


# --- the senseei arm ------------------------------------------------------


def test_the_senseei_arm_is_sent_to_the_application(client):
    code = check_in_arm(client, Arm.SENSEEI)
    participant = advance_to_intervention(client, code)
    page = client.get(f"/p/{code}").text

    assert "Open SENSEE-I" in page
    assert participant.participant_id in page


def test_the_senseei_arm_gets_no_harness_side_intervention(client):
    """Its session lives in the application; the harness only links to it."""
    code = check_in_arm(client, Arm.SENSEEI)
    participant = advance_to_intervention(client, code)

    assert participant.unguided is None
    assert participant.passive is None


# --- withdrawal -----------------------------------------------------------


def test_withdrawal_removes_the_participant_from_both_sides(client):
    participant_id, code = check_in(client)
    store = client.app.state.store

    assert store.withdraw(participant_id, link=client.app.state.link)

    assert store.get(participant_id) is None
    assert store.by_code(code) is None
