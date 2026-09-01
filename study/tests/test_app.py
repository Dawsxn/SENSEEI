"""The running trial, end to end: check-in, the three arms, and the gate.

The gate tests here matter more than the ones in test_phases.py. Those check the
rule; these check that no route around the outside of it exists — a hand-typed
URL, a resubmitted form, a participant who simply keeps clicking.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from study.arms import Arm
from study.interventions.unguided import OfflineChatBackend
from study.phases import Phase, ran_out_of_time, utcnow
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


def test_a_participant_who_finishes_early_goes_straight_on(client):
    """Nobody waits for the room."""
    _, code = check_in(client)
    participant = advance_to_intervention(client, code)

    client.post(f"/p/{code}/advance")

    assert participant.state.phase is Phase.POST_TEST_A


def test_finishing_early_is_not_recorded_as_running_out_of_time(client):
    _, code = check_in(client)
    participant = advance_to_intervention(client, code)

    client.post(f"/p/{code}/advance")

    assert not ran_out_of_time(participant.state)


def test_the_period_ends_a_session_that_is_still_running(client):
    """Enforced when their page is served, so a stalled tab does not evade it."""
    _, code = check_in(client)
    participant = advance_to_intervention(client, code)

    participant.state = replace(
        participant.state,
        intervention_started_at=utcnow() - timedelta(minutes=41),
    )
    client.get(f"/p/{code}")

    assert participant.state.phase is Phase.POST_TEST_A
    assert ran_out_of_time(participant.state)


def test_the_period_also_ends_a_session_on_a_chat_attempt(client):
    """Not only on a page load: the deadline must hold on every route."""
    code = check_in_arm(client, Arm.UNGUIDED_LLM)
    participant = advance_to_intervention(client, code)

    participant.state = replace(
        participant.state,
        intervention_started_at=utcnow() - timedelta(minutes=41),
    )
    response = client.post(f"/p/{code}/chat", data={"message": "one more"})

    assert response.status_code == 409
    assert participant.state.phase is Phase.POST_TEST_A


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


# --- instruments ----------------------------------------------------------


def test_an_instrument_renders_its_items(client):
    _, code = check_in(client)
    page = client.get(f"/p/{code}").text

    assert "What is your year level?" in page
    assert 'name="item_year_level"' in page


def test_an_instrument_hides_what_only_reviewers_may_see(client):
    """Correct answers, attention checks and pairings live in the review doc."""
    _, code = check_in(client)
    page = client.get(f"/p/{code}").text.lower()

    for word in ("attention check", "correct", "pairs with"):
        assert word not in page


def test_a_complete_submission_advances_the_participant(client):
    _, code = check_in(client)
    participant = client.app.state.store.by_code(code)

    client.post(f"/p/{code}/submit", data={
        "item_year_level": "3",
        "item_department": "Management and Organization",
        "item_prior_course": "no",
    })

    assert participant.state.phase is Phase.PRE_TEST


def test_an_incomplete_submission_does_not_advance(client):
    _, code = check_in(client)
    participant = client.app.state.store.by_code(code)

    client.post(f"/p/{code}/submit", data={"item_year_level": "3"})

    assert participant.state.phase is Phase.DEMOGRAPHICS


def test_an_incomplete_submission_keeps_the_answers_already_given(client):
    """Losing them to a bounce is the fastest way to get a careless retry."""
    _, code = check_in(client)

    client.post(f"/p/{code}/submit", data={"item_year_level": "3"})
    page = client.get(f"/p/{code}").text

    assert 'value="3" checked' in page or 'value="3"\n                   checked' in page
    assert "answer every question" in page


def test_a_submission_is_recorded(client):
    _, code = check_in(client)
    participant = client.app.state.store.by_code(code)

    client.post(f"/p/{code}/submit", data={
        "item_year_level": "3",
        "item_department": "MOD",
        "item_prior_course": "yes",
    })

    result = participant.responses[Phase.DEMOGRAPHICS]
    assert result.answers["prior_course"] == "yes"
    assert result.screening == {"prior_course": "yes"}


def test_a_placeholder_instrument_can_be_skipped(client):
    """The pre-test has no content yet; it must not block a rehearsal."""
    _, code = check_in(client)
    participant = client.app.state.store.by_code(code)
    client.post(f"/p/{code}/submit", data={
        "item_year_level": "3", "item_department": "MOD", "item_prior_course": "no",
    })

    assert "no content yet" in client.get(f"/p/{code}").text
    client.post(f"/p/{code}/advance")
    assert participant.state.phase is Phase.INTERVENTION


def test_the_console_warns_that_instruments_are_not_ready(client):
    assert "Instruments not ready" in client.get("/").text


def test_a_failed_attention_check_reaches_the_console(client):
    """§4.6.3's one categorical exclusion has to be visible to the proctor."""
    from study.instruments.schema import Instrument, Item, ItemType, Option

    check = Item(
        id="attn", type=ItemType.MULTIPLE_CHOICE, text="Choose B.",
        options=(Option("a", "A"), Option("b", "B")), attention_expected="b",
    )
    client.app.state.instruments["demographics"] = Instrument(
        id="demographics", title="About you", phase="demographics", items=(check,)
    )

    _, code = check_in(client)
    client.post(f"/p/{code}/submit", data={"item_attn": "a"})

    assert "1/1" not in client.get("/").text  # 0 of 1 passed
    assert "0/1" in client.get("/").text


def test_withdrawal_removes_the_participant_from_both_sides(client):
    participant_id, code = check_in(client)
    store = client.app.state.store

    assert store.withdraw(participant_id, link=client.app.state.link)

    assert store.get(participant_id) is None
    assert store.by_code(code) is None


def test_the_console_offers_withdrawal_with_a_confirmation(client):
    """§4.7.1 is unconditional, and the deletion is not reversible."""
    participant_id, _ = check_in(client)
    page = client.get("/").text

    assert f"/participants/{participant_id}/withdraw" in page
    assert "cannot be undone" in page


def test_the_console_links_to_the_grading_summary(client):
    assert "/agreement" in client.get("/").text
