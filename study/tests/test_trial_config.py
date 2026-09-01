"""Trial configuration: the model pin, the reading, and the checks before a run."""

from __future__ import annotations

import pytest

from study.arms import ALL_ARMS
from study.trial_config import (
    LLMConfig,
    ReadingConfig,
    TrialConfig,
    TrialConfigError,
    assert_model_parity,
    load_trial_config,
)

REPO_CONFIG = "study/trial.yaml"


@pytest.fixture
def reading(tmp_path):
    path = tmp_path / "reading.txt"
    path.write_text("Strategy is a company's plan for competing.", encoding="utf-8")
    return ReadingConfig(path=path, title="Strategy", core_components=("plan",))


@pytest.fixture
def config(reading):
    return TrialConfig(
        trial_id="test-run",
        reading=reading,
        allocation_seed=42,
        senseei_base_url="https://senseei.test",
    )


# --- the reading ----------------------------------------------------------


def test_reading_is_read_from_its_file(config):
    assert "Strategy" in config.reading.text()


def test_checksum_detects_a_diverged_copy(reading, tmp_path):
    """The two arms' copies must be identical or the stimulus differs (§4.6.2)."""
    before = reading.checksum()

    other = tmp_path / "other.txt"
    other.write_text("Strategy is a company's plan for competing!", encoding="utf-8")
    after = ReadingConfig(path=other, title="Strategy").checksum()

    assert before != after


def test_checksum_is_stable_across_reads(reading):
    assert reading.checksum() == reading.checksum()


def test_a_missing_reading_is_refused(tmp_path):
    config = TrialConfig(
        trial_id="t",
        reading=ReadingConfig(path=tmp_path / "gone.txt", title="x"),
        allocation_seed=1,
        senseei_base_url="https://senseei.test",
    )
    with pytest.raises(TrialConfigError, match="Reading not found"):
        config.validate()


def test_an_empty_reading_is_refused(tmp_path):
    path = tmp_path / "blank.txt"
    path.write_text("   \n", encoding="utf-8")
    config = TrialConfig(
        trial_id="t",
        reading=ReadingConfig(path=path, title="x"),
        allocation_seed=1,
        senseei_base_url="https://senseei.test",
    )
    with pytest.raises(TrialConfigError, match="is empty"):
        config.validate()


# --- the model ------------------------------------------------------------


def test_provider_settings_ask_for_prose_not_json():
    """The unguided arm is a chat; only the Assessment Agent needs JSON."""
    assert LLMConfig().provider_settings()["json_mode"] is False


def test_temperature_is_omitted_unless_pinned():
    """Unset means the provider default, which is what an ordinary chat uses."""
    assert "temperature" not in LLMConfig().provider_settings()
    assert LLMConfig(temperature=0.7).provider_settings()["temperature"] == 0.7


def test_parity_passes_when_the_arms_share_a_model(config):
    assert_model_parity(config, config.llm.fingerprint)


def test_parity_fails_on_a_different_model(config):
    """§4.6.2: differing models would confound scaffolding with capability."""
    with pytest.raises(TrialConfigError, match="parity is broken"):
        assert_model_parity(config, "gemini:gemini-2.0-flash")


def test_parity_fails_when_the_app_cannot_report_its_model(config):
    """Unverified is not the same as verified, and must not pass silently."""
    with pytest.raises(TrialConfigError, match="Cannot verify model parity"):
        assert_model_parity(config, None)


def test_a_synthetic_provider_is_refused_for_real_collection(reading):
    config = TrialConfig(
        trial_id="t",
        reading=reading,
        llm=LLMConfig(provider="mock"),
        allocation_seed=1,
        senseei_base_url="https://senseei.test",
    )
    with pytest.raises(TrialConfigError, match="cannot produce real responses"):
        config.validate()


def test_a_synthetic_provider_is_fine_for_a_dry_run(reading):
    TrialConfig(
        trial_id="t",
        reading=reading,
        llm=LLMConfig(provider="mock"),
        dry_run=True,
    ).validate()


# --- the run --------------------------------------------------------------


def test_a_valid_configuration_passes(config):
    config.validate()


def test_an_unset_seed_is_refused_for_real_collection(reading):
    """Without a recorded seed the allocation cannot be audited afterwards."""
    config = TrialConfig(
        trial_id="t",
        reading=reading,
        allocation_seed=0,
        senseei_base_url="https://senseei.test",
    )
    with pytest.raises(TrialConfigError, match="allocation_seed"):
        config.validate()


def test_the_senseei_arm_must_have_somewhere_to_go(reading):
    config = TrialConfig(trial_id="t", reading=reading, allocation_seed=1)
    with pytest.raises(TrialConfigError, match="senseei_base_url"):
        config.validate()


def test_every_problem_is_reported_at_once(tmp_path):
    """One pre-flight should surface everything, not fail one item at a time."""
    config = TrialConfig(
        trial_id="",
        reading=ReadingConfig(path=tmp_path / "gone.txt", title=""),
        allocation_seed=0,
        senseei_base_url="",
    )
    with pytest.raises(TrialConfigError) as exc:
        config.validate()

    message = str(exc.value)
    for expected in ("trial_id", "Reading not found", "allocation_seed", "senseei_base_url"):
        assert expected in message


def test_allocation_follows_the_pinned_seed(config):
    assert config.allocation().counts() == {arm: 15 for arm in ALL_ARMS}
    assert config.allocation().sequence == config.allocation().sequence


def test_an_unworkable_cohort_is_caught_by_validation(reading):
    config = TrialConfig(
        trial_id="t",
        reading=reading,
        participants=45,
        block_size=6,  # leaves a partial block
        allocation_seed=1,
        senseei_base_url="https://senseei.test",
    )
    with pytest.raises(TrialConfigError, match="partial block"):
        config.validate()


def test_timing_follows_the_configured_minutes(reading):
    config = TrialConfig(trial_id="t", reading=reading, intervention_minutes=12)
    assert config.timing.intervention_seconds == 12 * 60


def test_one_sitting_puts_both_ai_arms_on_the_provider_at_once(config):
    """30 of 45 concurrent — the number the rate limit has to survive."""
    assert config.concurrent_ai_participants == 30


def test_staggered_sittings_carry_no_single_peak(reading):
    config = TrialConfig(trial_id="t", reading=reading, one_sitting=False)
    assert config.concurrent_ai_participants == 0


def test_the_stamp_carries_what_reproduction_needs(config):
    stamp = config.stamp()
    for key in ("model", "reading_checksum", "allocation_seed", "trial_id"):
        assert stamp[key] not in (None, "")


# --- the file in the repo -------------------------------------------------


def test_the_repo_config_loads():
    config = load_trial_config(REPO_CONFIG)
    assert config.llm.provider == "gemini"
    assert config.participants == 45
    assert config.intervention_minutes == 40


def test_the_repo_config_ships_as_a_dry_run():
    """It has no seed, reading or app URL yet, so it must not claim to be live."""
    assert load_trial_config(REPO_CONFIG).dry_run is True


def test_the_repo_config_matches_the_only_other_pinned_model():
    """Until the app has settings, the eval's config.yaml is the reference pin."""
    import yaml

    with open("assessment-agent-eval/config.yaml", encoding="utf-8") as f:
        eval_config = yaml.safe_load(f)

    trial = load_trial_config(REPO_CONFIG)
    assert trial.llm.model == eval_config["model"]
    assert trial.llm.provider == eval_config["provider"]


def test_a_missing_config_file_says_so():
    with pytest.raises(TrialConfigError, match="No trial configuration"):
        load_trial_config("study/nonexistent.yaml")
