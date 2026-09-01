"""The passive control arm: time actually spent on the text, and how far down it."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from study.interventions.passive import PassiveSession, ScrollSample

T0 = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def session() -> PassiveSession:
    return PassiveSession("P-001", started_at=T0)


# --- time on text ---------------------------------------------------------


def test_a_full_sitting_counts_the_whole_period():
    live = session()
    live.close(at(40))
    assert live.telemetry().time_on_text == timedelta(minutes=40)


def test_time_away_from_the_reading_does_not_count():
    """Phase duration and time on text are different questions (§4.6.3)."""
    live = session()
    live.went_away(at(6))
    live.came_back(at(30))
    live.close(at(40))

    telemetry = live.telemetry()
    assert telemetry.time_on_text == timedelta(minutes=16)
    assert telemetry.away_count == 1


def test_leaving_and_never_returning_stops_the_clock():
    live = session()
    live.went_away(at(6))
    live.close(at(40))
    assert live.telemetry().time_on_text == timedelta(minutes=6)


def test_repeat_departures_are_each_counted():
    live = session()
    for start, end in ((5, 10), (15, 20), (25, 30)):
        live.went_away(at(start))
        live.came_back(at(end))
    live.close(at(40))

    telemetry = live.telemetry()
    assert telemetry.away_count == 3
    assert telemetry.time_on_text == timedelta(minutes=25)


def test_a_repeated_away_event_is_not_a_second_departure():
    """Browsers fire these twice; counting both would overstate distraction."""
    live = session()
    live.went_away(at(6))
    live.went_away(at(7))
    live.came_back(at(10))
    live.close(at(40))

    telemetry = live.telemetry()
    assert telemetry.away_count == 1
    assert telemetry.time_on_text == timedelta(minutes=36)


def test_a_repeated_return_event_does_not_restart_the_clock():
    live = session()
    live.went_away(at(6))
    live.came_back(at(10))
    live.came_back(at(20))
    live.close(at(40))

    assert live.telemetry().time_on_text == timedelta(minutes=36)


def test_time_on_text_can_be_read_mid_session():
    live = session()
    assert live.time_on_text(now=at(12)) == timedelta(minutes=12)


def test_an_out_of_order_event_cannot_inflate_time_on_text():
    """A clock adjustment must not hand a participant credit they did not earn."""
    live = session()
    live.went_away(at(-5))
    live.close(at(40))
    assert live.telemetry().time_on_text == timedelta()


def test_closing_twice_keeps_the_first_end_time():
    live = session()
    live.close(at(40))
    live.close(at(50))
    assert live.telemetry().ended_at == at(40)
    assert live.telemetry().time_on_text == timedelta(minutes=40)


# --- scroll depth ---------------------------------------------------------


def test_the_furthest_point_reached_is_kept():
    """Scrolling back up does not un-read the bottom of the text."""
    live = session()
    for depth in (0.1, 0.6, 0.9, 0.2):
        live.scrolled(depth, at(1))
    live.close(at(40))

    assert live.telemetry().max_scroll_depth == pytest.approx(0.9)


def test_never_scrolling_reads_as_the_top_of_the_text():
    live = session()
    live.close(at(40))
    assert live.telemetry().max_scroll_depth == 0.0


def test_samples_are_counted():
    live = session()
    for _ in range(5):
        live.scrolled(0.5, at(1))
    assert live.telemetry().sample_count == 5


@pytest.mark.parametrize("depth", [-0.1, 1.1, 2.0])
def test_an_impossible_scroll_depth_is_refused(depth):
    with pytest.raises(ValueError, match="within 0..1"):
        ScrollSample(at=T0, depth=depth)


@pytest.mark.parametrize("depth", [0.0, 0.5, 1.0])
def test_the_bounds_themselves_are_valid(depth):
    assert ScrollSample(at=T0, depth=depth).depth == depth


# --- the record -----------------------------------------------------------


def test_the_session_starts_open():
    assert session().is_open


def test_the_session_is_closed_at_the_end():
    live = session()
    live.close(at(40))
    assert not live.is_open


def test_telemetry_carries_what_the_exclusion_criterion_needs():
    live = session()
    live.scrolled(0.8, at(20))
    live.close(at(40))

    telemetry = live.telemetry()
    assert telemetry.participant_id == "P-001"
    assert telemetry.time_on_text > timedelta()
    assert telemetry.max_scroll_depth > 0
