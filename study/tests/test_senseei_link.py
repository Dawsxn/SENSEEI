"""The seam to the SENSEE-I application, and the fake that stands in for it."""

from __future__ import annotations

from study.senseei_link import FakeSenseeiLink, SenseeiLink


def test_the_fake_satisfies_the_protocol():
    """Swapping in the real link must not require changing any caller."""
    assert isinstance(FakeSenseeiLink(), SenseeiLink)


def test_the_fake_is_marked_as_unfit_for_real_collection():
    assert FakeSenseeiLink().is_synthetic is True


def test_telemetry_is_stable_for_a_participant():
    """A dry run must be repeatable, or its export cannot be diffed."""
    a = FakeSenseeiLink().fetch_telemetry("P-007")
    b = FakeSenseeiLink().fetch_telemetry("P-007")
    assert a == b


def test_different_participants_get_different_sessions():
    link = FakeSenseeiLink()
    sessions = {link.fetch_telemetry(f"P-{i:03d}").session_id for i in range(10)}
    assert len(sessions) == 10


def test_the_fake_covers_every_session_ending():
    """A dry run should exercise fallbacks and cut-offs, not one happy path."""
    link = FakeSenseeiLink()
    endings = {link.fetch_telemetry(f"P-{i:03d}").status for i in range(45)}
    assert endings == {"complete", "fallback", "unfinished"}


def test_telemetry_carries_what_the_exclusion_criteria_need():
    """§4.6.3 excludes on session time or turn count falling below a threshold."""
    telemetry = FakeSenseeiLink().fetch_telemetry("P-001")
    assert telemetry.duration is not None
    assert telemetry.turn_count > 0


def test_telemetry_carries_provenance():
    """Without these, a mid-collection prompt change is invisible in the data."""
    telemetry = FakeSenseeiLink().fetch_telemetry("P-001")
    assert telemetry.rubric_version
    assert telemetry.prompt_version
    assert telemetry.model


def test_attempts_are_recorded_per_step():
    telemetry = FakeSenseeiLink().fetch_telemetry("P-004")
    assert telemetry.total_attempts == sum(telemetry.attempts_per_step.values())
    assert telemetry.highest_step in telemetry.attempts_per_step


def test_withdrawal_removes_the_session():
    """§4.7.1: a participant may withdraw at any point and have their data deleted."""
    link = FakeSenseeiLink()
    assert link.fetch_telemetry("P-002") is not None

    assert link.delete_participant_data("P-002") == 1
    assert link.fetch_telemetry("P-002") is None


def test_deleting_twice_removes_nothing_further():
    link = FakeSenseeiLink()
    link.delete_participant_data("P-002")
    assert link.delete_participant_data("P-002") == 0


def test_session_url_is_per_participant():
    link = FakeSenseeiLink(base_url="https://senseei.test/s/")
    assert link.session_url("P-011") == "https://senseei.test/s/P-011"
