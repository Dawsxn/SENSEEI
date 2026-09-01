"""Randomisation must produce exactly 15/15/15, and stay balanced if it stops early."""

from __future__ import annotations

import pytest

from study.arms import ALL_ARMS, Arm
from study.randomisation import (
    DEFAULT_BLOCK_SIZE,
    AllocationError,
    generate_allocation,
    max_imbalance,
)

TRIAL_N = 45  # §4.6.3: 45 participants, 15 per arm


def test_full_trial_splits_exactly_fifteen_each():
    allocation = generate_allocation(TRIAL_N, seed=20260901)
    assert allocation.counts() == {arm: 15 for arm in ALL_ARMS}


def test_every_prefix_stays_balanced_within_one_block():
    """A batch cut short must not leave the arms lopsided.

    This is the whole reason for blocking. With independent draws a run that
    stops at 30 could easily be 14/9/7; here the gap is bounded by construction.
    """
    allocation = generate_allocation(TRIAL_N, seed=7)
    ceiling = DEFAULT_BLOCK_SIZE - DEFAULT_BLOCK_SIZE // len(ALL_ARMS)
    assert max_imbalance(allocation) <= ceiling


def test_balanced_at_every_block_boundary():
    allocation = generate_allocation(TRIAL_N, seed=99)
    per_block = DEFAULT_BLOCK_SIZE // len(ALL_ARMS)

    for block in range(TRIAL_N // DEFAULT_BLOCK_SIZE):
        upto = allocation.sequence[: (block + 1) * DEFAULT_BLOCK_SIZE]
        for arm in ALL_ARMS:
            assert upto.count(arm) == (block + 1) * per_block


def test_same_seed_reproduces_the_sequence():
    """The allocation is auditable: anyone with the seed can re-derive it."""
    a = generate_allocation(TRIAL_N, seed=4242)
    b = generate_allocation(TRIAL_N, seed=4242)
    assert a.sequence == b.sequence


def test_different_seeds_differ():
    a = generate_allocation(TRIAL_N, seed=1)
    b = generate_allocation(TRIAL_N, seed=2)
    assert a.sequence != b.sequence


def test_arm_for_follows_check_in_order():
    allocation = generate_allocation(TRIAL_N, seed=11)
    assert [allocation.arm_for(i) for i in range(TRIAL_N)] == list(allocation.sequence)


def test_running_past_the_end_is_an_error_not_an_extra_draw():
    """More arrivals than recruited is a decision for a human, not a silent draw."""
    allocation = generate_allocation(9, seed=3)
    with pytest.raises(IndexError, match="past the end"):
        allocation.arm_for(9)


def test_partial_final_block_is_refused():
    """45 does not divide into blocks of 6; refusing beats uneven groups."""
    with pytest.raises(AllocationError, match="partial block"):
        generate_allocation(TRIAL_N, seed=1, block_size=6)


def test_error_names_the_block_sizes_that_would_work():
    with pytest.raises(AllocationError) as exc:
        generate_allocation(TRIAL_N, seed=1, block_size=6)
    assert "[3, 9, 15, 45]" in str(exc.value)


def test_block_size_must_cover_every_arm_equally():
    with pytest.raises(AllocationError, match="not a multiple"):
        generate_allocation(TRIAL_N, seed=1, block_size=4)


def test_rejects_empty_trial():
    with pytest.raises(AllocationError):
        generate_allocation(0, seed=1)


@pytest.mark.parametrize("seed", range(25))
def test_totals_hold_across_many_seeds(seed):
    """No seed may produce unequal groups — the guarantee is structural."""
    allocation = generate_allocation(TRIAL_N, seed=seed)
    assert set(allocation.counts().values()) == {15}


def test_allocation_is_not_a_fixed_rotation():
    """Blocks are shuffled; a predictable cycle would let assignment be guessed."""
    allocation = generate_allocation(TRIAL_N, seed=5)
    rotation = [ALL_ARMS[i % len(ALL_ARMS)] for i in range(TRIAL_N)]
    assert list(allocation.sequence) != rotation


def test_arm_labels_are_distinct_and_only_senseei_takes_sus():
    assert len({arm.label for arm in ALL_ARMS}) == len(ALL_ARMS)
    assert [arm for arm in ALL_ARMS if arm.takes_sus] == [Arm.SENSEEI]
