"""The three trial arms (Section 4.6.2).

The arm is the study's independent variable: the mode of instruction a
participant is assigned to. It is written once at check-in and never changes.
"""

from __future__ import annotations

from enum import Enum


class Arm(str, Enum):
    """One of the three instructional modes under comparison."""

    #: The SENSEE-I platform itself. Runs in the app, not in this harness.
    SENSEEI = "senseei"

    #: Active control: a general-purpose LLM chat with no pedagogical system
    #: prompt and no constraint on use, on the same model as SENSEE-I's agents.
    UNGUIDED_LLM = "unguided_llm"

    #: Passive control: the same expository text, read without any tool.
    PASSIVE = "passive"

    @property
    def label(self) -> str:
        """Human-readable name, for the proctor console and exports."""
        return {
            Arm.SENSEEI: "SENSEE-I",
            Arm.UNGUIDED_LLM: "Unguided LLM",
            Arm.PASSIVE: "Passive control",
        }[self]

    @property
    def takes_sus(self) -> bool:
        """Whether this arm answers the System Usability Scale.

        Only the SENSEE-I group does (Table 4.11) — there is no platform for the
        control arms to rate.
        """
        return self is Arm.SENSEEI


#: Canonical ordering, used wherever arms are listed or a block is built.
ALL_ARMS: tuple[Arm, ...] = (Arm.SENSEEI, Arm.UNGUIDED_LLM, Arm.PASSIVE)
