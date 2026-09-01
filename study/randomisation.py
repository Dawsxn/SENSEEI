"""Permuted-block randomisation of participants to arms (Section 4.6.3).

The manuscript requires 45 participants, 15 per arm, with assignment to a
condition made at random. Drawing each participant's arm independently would not
deliver that: over 45 independent draws the arms land on 15/15/15 only about 2%
of the time, and the study would report unequal groups it never intended.

So the allocation is a *sequence*, generated once before collection begins and
consumed one slot at a time as participants check in. Within each block every
arm appears equally often, and the block is shuffled, so the totals are exact
while the next assignment stays unpredictable.

Two properties this buys, both of which matter for a trial run in batches over
several days:

1. **Exact totals.** ``n`` participants split exactly evenly across the arms.
2. **Balance at every prefix.** If only 38 of 45 people show up, the arms are
   still near-even, because imbalance can never exceed one block's worth. With
   independent draws a short-fall could leave the arms badly lopsided.

The sequence is generated from a recorded seed so the allocation is reproducible
and auditable after the fact, which is what lets someone verify the assignment
was not adjusted mid-study.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

from .arms import ALL_ARMS, Arm

#: Participants per block. Must be a multiple of the number of arms, and must
#: divide the total. For n=45 the valid sizes are 3, 9, 15 and 45.
#:
#: 9 (three per arm) is the default as a middle ground. Smaller blocks track the
#: even split more tightly but become guessable — with blocks of 3, whoever
#: checks people in knows the third participant's arm from the first two.
DEFAULT_BLOCK_SIZE = 9


class AllocationError(ValueError):
    """The requested allocation cannot produce balanced groups."""


@dataclass(frozen=True)
class Allocation:
    """A pre-generated assignment sequence, fixed before collection begins."""

    seed: int
    block_size: int
    sequence: tuple[Arm, ...]

    def __len__(self) -> int:
        return len(self.sequence)

    def arm_for(self, position: int) -> Arm:
        """The arm for the participant at ``position`` (0-based, in check-in order).

        Position is the participant's place in the check-in queue, so the same
        allocation always yields the same assignment. Raises IndexError once the
        sequence is exhausted, which means more people showed up than were
        recruited — a situation that needs a decision, not a silent extra draw.
        """
        if position < 0:
            raise IndexError(f"Position must be non-negative, got {position}")
        if position >= len(self.sequence):
            raise IndexError(
                f"Allocation holds {len(self.sequence)} slots; position {position} "
                "is past the end. Generate a longer allocation before enrolling more."
            )
        return self.sequence[position]

    def counts(self) -> dict[Arm, int]:
        """How many slots each arm holds in total."""
        tally = Counter(self.sequence)
        return {arm: tally.get(arm, 0) for arm in ALL_ARMS}


def generate_allocation(
    n: int,
    seed: int,
    block_size: int = DEFAULT_BLOCK_SIZE,
) -> Allocation:
    """Build the allocation sequence for ``n`` participants.

    Raises AllocationError rather than silently producing uneven groups: a
    partial final block would put one arm ahead of another, and finding that out
    during analysis is far worse than finding it out now.
    """
    if n <= 0:
        raise AllocationError(f"Need at least one participant, got {n}")

    n_arms = len(ALL_ARMS)
    if block_size % n_arms != 0:
        raise AllocationError(
            f"Block size {block_size} is not a multiple of the {n_arms} arms, so a "
            "block cannot hold each arm equally often."
        )
    if n % block_size != 0:
        valid = [s for s in range(n_arms, n + 1, n_arms) if n % s == 0]
        raise AllocationError(
            f"{n} participants do not divide into blocks of {block_size}, which "
            f"would leave a partial block and uneven groups. Valid block sizes "
            f"for n={n}: {valid}."
        )

    per_arm_per_block = block_size // n_arms
    rng = random.Random(seed)

    sequence: list[Arm] = []
    for _ in range(n // block_size):
        block = [arm for arm in ALL_ARMS for _ in range(per_arm_per_block)]
        rng.shuffle(block)
        sequence.extend(block)

    return Allocation(seed=seed, block_size=block_size, sequence=tuple(sequence))


def max_imbalance(allocation: Allocation) -> int:
    """Largest gap between any two arms at any point in the sequence.

    Useful as a sanity check and for reporting: it is the worst the groups can
    look if collection stops early. Bounded by ``block_size - block_size/n_arms``
    by construction.
    """
    tally: Counter[Arm] = Counter()
    worst = 0
    for arm in allocation.sequence:
        tally[arm] += 1
        spread = max(tally.get(a, 0) for a in ALL_ARMS) - min(
            tally.get(a, 0) for a in ALL_ARMS
        )
        worst = max(worst, spread)
    return worst
