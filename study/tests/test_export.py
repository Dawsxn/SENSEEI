"""The export: everything the analysis needs, and nothing the raters must not see."""

from __future__ import annotations

import csv
import json

import pytest
from fastapi.testclient import TestClient

from study.api.app import RATERS, create_app
from study.api.store import TrialStore
from study.arms import Arm
from study.export import export_analysis, export_for_raters
from study.grading import DIMENSIONS
from study.instruments.schema import Instrument, Item, ItemType
from study.interventions.unguided import OfflineChatBackend
from study.persistence import Repository
from study.phases import Phase, utcnow
from study.senseei_link import FakeSenseeiLink
from study.trial_config import load_trial_config

DISTINCTIVE = "Evangelina Featherstonehaugh"


@pytest.fixture
def config():
    return load_trial_config("study/trial.yaml")


@pytest.fixture
def link():
    return FakeSenseeiLink()


@pytest.fixture
def store(config, tmp_path):
    return TrialStore(
        config,
        chat_backend=OfflineChatBackend(),
        repository=Repository(f"sqlite:///{tmp_path / 'trial.db'}"),
    )


@pytest.fixture
def client(config, store):
    app = create_app(config=config, store=store)
    # Give the SBA real content so responses exist to export and grade.
    app.state.instruments["sba"] = Instrument(
        id="sba", title="Applying what you read", phase="sba",
        stimulus="A bakery is offered cheaper flour.",
        items=(Item(id="sba_response", type=ItemType.LONG_TEXT, text="Advise them."),),
    )
    return TestClient(app)


def run_participants(client, count=6):
    """Walk `count` participants all the way to a written SBA response."""
    for index in range(count):
        client.post("/check-in", data={
            "name": DISTINCTIVE if index == 0 else f"Person {index}",
            "consent_form_serial": f"CF-{index}",
        })
        participant = client.app.state.store.all()[-1]
        code = participant.access_code

        client.post(f"/p/{code}/submit", data={
            "item_year_level": "3", "item_department": "MOD",
            "item_prior_course": "no",
        })
        client.post(f"/p/{code}/advance")           # pre-test stub
        if participant.arm is Arm.UNGUIDED_LLM:
            client.post(f"/p/{code}/chat", data={"message": "what is this about"})
        if participant.arm is Arm.PASSIVE:
            client.post(f"/p/{code}/reading-event",
                        data={"kind": "scroll", "depth": 0.7})
        client.post(f"/p/{code}/advance")           # -> post-test A
        client.post(f"/p/{code}/advance")           # -> SBA
        client.post(f"/p/{code}/submit", data={
            "item_sba_response": f"Response from participant {index}. "
                                 "They would give up the accumulated fit.",
        })
    return client.app.state.store


def read(directory, name) -> list[dict]:
    path = directory / name
    text = path.read_text(encoding="utf-8")
    return list(csv.DictReader(text.splitlines())) if text.strip() else []


# --- the analysis bundle --------------------------------------------------


def test_the_bundle_has_a_file_for_every_analysis(client, tmp_path, link):
    store = run_participants(client)
    result = export_analysis(store, tmp_path / "out", link=link)

    for name in (
        "participants.csv", "instrument_scores.csv", "instrument_answers.csv",
        "phase_durations.csv", "sba_responses.csv", "manifest.json",
    ):
        assert name in result.files


def test_every_participant_appears(client, tmp_path, link):
    store = run_participants(client)
    export_analysis(store, tmp_path / "out", link=link)

    assert len(read(tmp_path / "out", "participants.csv")) == 6


def test_the_exclusion_measures_are_exported(client, tmp_path, link):
    """§4.6.3's quantities, so the thresholds can be applied in the analysis."""
    store = run_participants(client)
    export_analysis(store, tmp_path / "out", link=link)
    rows = read(tmp_path / "out", "participants.csv")

    headers = set().union(*(r.keys() for r in rows))
    assert {"arm", "attention_failed", "ran_out_of_time"} <= headers
    assert headers & {"word_count", "turn_count", "time_on_text_seconds"}


def test_no_threshold_has_been_applied(client, tmp_path, link):
    """The export reports numbers; exclusion is the analysis's decision."""
    store = run_participants(client)
    export_analysis(store, tmp_path / "out", link=link)
    rows = read(tmp_path / "out", "participants.csv")

    headers = set().union(*(r.keys() for r in rows))
    assert not any("exclud" in h.lower() for h in headers)


def test_item_answers_are_long_form(client, tmp_path, link):
    """One row per answer: instruments differ in length, and a wide table would
    break the moment an item is added."""
    store = run_participants(client)
    export_analysis(store, tmp_path / "out", link=link)
    rows = read(tmp_path / "out", "instrument_answers.csv")

    assert {"participant_id", "instrument", "item_id", "answer"} <= set(rows[0])
    assert any(r["item_id"] == "year_level" for r in rows)


def test_phase_durations_are_exported(client, tmp_path, link):
    """Time-on-task varies now, so the analysis needs it."""
    store = run_participants(client)
    export_analysis(store, tmp_path / "out", link=link)
    rows = read(tmp_path / "out", "phase_durations.csv")

    assert any(r["phase"] == Phase.DEMOGRAPHICS.value for r in rows)


def test_unguided_transcripts_are_exported(client, tmp_path, link):
    store = run_participants(client)
    export_analysis(store, tmp_path / "out", link=link)
    rows = read(tmp_path / "out", "unguided_transcripts.csv")

    assert rows
    assert any(r["speaker"] == "participant" for r in rows)


def test_senseei_sessions_carry_their_versions(client, tmp_path, link):
    """A session graded under a different rubric is not the same session."""
    store = run_participants(client)
    export_analysis(store, tmp_path / "out", link=link)
    rows = read(tmp_path / "out", "senseei_sessions.csv")

    assert rows
    assert rows[0]["rubric_version"] and rows[0]["model"]


def test_the_manifest_records_what_produced_the_files(client, tmp_path, link):
    store = run_participants(client)
    export_analysis(store, tmp_path / "out", link=link)
    manifest = json.loads((tmp_path / "out" / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["participants"] == 6
    assert sum(manifest["by_arm"].values()) == 6
    assert "trial" in manifest


def test_an_empty_table_still_gets_a_file(config, store, tmp_path, link):
    """A missing file is ambiguous; an empty one is not."""
    result = export_analysis(store, tmp_path / "out", link=link)
    assert "participants.csv" in result.files


# --- no identity anywhere (§4.6.6, §4.7.4) --------------------------------


def test_no_exported_file_contains_a_name(client, tmp_path, link):
    """The identity table exists and the export simply never reads it."""
    store = run_participants(client)
    export_analysis(store, tmp_path / "out", link=link)

    for path in (tmp_path / "out").iterdir():
        assert DISTINCTIVE not in path.read_text(encoding="utf-8"), path.name


def test_everything_is_keyed_to_the_participant_id(client, tmp_path, link):
    store = run_participants(client)
    export_analysis(store, tmp_path / "out", link=link)

    for name in ("participants.csv", "instrument_answers.csv", "sba_responses.csv"):
        rows = read(tmp_path / "out", name)
        assert rows and all(r["participant_id"].startswith("P-") for r in rows)


# --- the rater bundle -----------------------------------------------------


def test_the_rater_file_shows_no_arm(client, tmp_path):
    """§4.6.5 requires blind grading; an arm column would end it."""
    store = run_participants(client)
    export_for_raters(store, RATERS, tmp_path / "out")
    rows = read(tmp_path / "out", "rater_rater_a.csv")

    assert rows
    assert "arm" not in rows[0]
    assert all("senseei" not in " ".join(r.values()).lower() for r in rows)


def test_the_rater_file_shows_no_participant_id(client, tmp_path):
    store = run_participants(client)
    export_for_raters(store, RATERS, tmp_path / "out")
    text = (tmp_path / "out" / "rater_rater_a.csv").read_text(encoding="utf-8")

    assert "P-001" not in text
    assert "R-" in text


def test_each_rater_gets_a_different_order(client, tmp_path):
    store = run_participants(client)
    export_for_raters(store, RATERS, tmp_path / "out")

    first = [r["response_id"] for r in read(tmp_path / "out", "rater_rater_a.csv")]
    second = [r["response_id"] for r in read(tmp_path / "out", "rater_rater_b.csv")]

    assert sorted(first) == sorted(second)
    assert first != second


def test_the_rater_file_has_empty_score_columns(client, tmp_path):
    store = run_participants(client)
    export_for_raters(store, RATERS, tmp_path / "out")
    rows = read(tmp_path / "out", "rater_rater_a.csv")

    assert set(DIMENSIONS) <= set(rows[0])
    assert all(row[d] == "" for row in rows for d in DIMENSIONS)


def test_the_key_is_written_separately_from_the_rater_files(client, tmp_path):
    """It maps blind ids back to participants and is for the team alone."""
    store = run_participants(client)
    export_for_raters(store, RATERS, tmp_path / "out")

    key = read(tmp_path / "out", "rater_key.csv")
    assert key and {"response_id", "participant_id"} == set(key[0])
    assert "rater_key" not in (tmp_path / "out" / "rater_rater_a.csv").read_text(
        encoding="utf-8"
    )


def test_a_subset_can_be_graded(client, tmp_path):
    """§4.6.5 grades a representative subset, not necessarily everyone."""
    store = run_participants(client)
    result = export_for_raters(store, RATERS, tmp_path / "out", subset=3, seed=7)

    assert result.sba_responses == 3
    assert len(read(tmp_path / "out", "rater_rater_a.csv")) == 3


# --- the rating interface -------------------------------------------------


def test_a_rater_sees_one_response_at_a_time(client):
    """A list would let them read ahead and score relative to their neighbours."""
    run_participants(client)
    page = client.get("/rate/rater-a").text

    assert page.count('name="response_id"') == 1


def test_the_rating_screen_shows_no_arm_or_participant(client):
    run_participants(client)
    page = client.get("/rate/rater-a").text.lower()

    assert "p-001" not in page
    assert "unguided" not in page and "passive control" not in page


def test_a_score_is_recorded_and_the_next_response_appears(client):
    run_participants(client)
    first = client.get("/rate/rater-a").text
    response_id = first.split('name="response_id" value="')[1].split('"')[0]

    client.post("/rate/rater-a", data={
        "response_id": response_id,
        "concept_retrieval": "3",
        "scenario_application": "2",
        "analytical_justification": "2",
    })

    assert response_id not in client.get("/rate/rater-a").text


def test_a_partial_score_is_not_stored(client):
    """Table 4.12 has three dimensions; a partial one cannot be compared."""
    run_participants(client)
    page = client.get("/rate/rater-a").text
    response_id = page.split('name="response_id" value="')[1].split('"')[0]

    client.post("/rate/rater-a", data={
        "response_id": response_id, "concept_retrieval": "3",
    })

    assert client.app.state.store.repository.scored_by("rater-a") == set()


def test_an_unknown_rater_cannot_grade(client):
    run_participants(client)
    assert client.get("/rate/stranger").status_code == 404


def test_agreement_reports_kappa_once_both_have_scored(client):
    run_participants(client)
    for rater, level in (("rater-a", "3"), ("rater-b", "2")):
        for _ in range(6):
            page = client.get(f"/rate/{rater}").text
            if 'name="response_id"' not in page:
                break
            response_id = page.split('name="response_id" value="')[1].split('"')[0]
            client.post(f"/rate/{rater}", data={
                "response_id": response_id,
                "concept_retrieval": level,
                "scenario_application": "2",
                "analytical_justification": "2",
            })

    page = client.get("/agreement").text
    assert "Cohen" in page
    assert "Disagreements" in page or "No disagreements" in page


def test_agreement_says_so_when_only_one_rater_has_worked(client):
    run_participants(client)
    page = client.get("/rate/rater-a").text
    response_id = page.split('name="response_id" value="')[1].split('"')[0]
    client.post("/rate/rater-a", data={
        "response_id": response_id, "concept_retrieval": "3",
        "scenario_application": "3", "analytical_justification": "3",
    })

    assert "compares two raters" in client.get("/agreement").text


def test_scores_survive_a_restart(client, config, tmp_path):
    run_participants(client)
    page = client.get("/rate/rater-a").text
    response_id = page.split('name="response_id" value="')[1].split('"')[0]
    client.post("/rate/rater-a", data={
        "response_id": response_id, "concept_retrieval": "3",
        "scenario_application": "3", "analytical_justification": "3",
    })

    repository = client.app.state.store.repository
    scores = Repository(repository.url).load_scores()

    assert len(scores) == 1
    assert scores[0].levels["concept_retrieval"] == 3
