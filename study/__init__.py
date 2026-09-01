"""Human-evaluation harness for the SENSEE-I randomised controlled trial.

This package is everything that *surrounds* the SENSEE-I application during the
three-arm RCT described in the manuscript's Section 4.6: participant lifecycle,
randomisation, the phase engine that paces a session, the two control-arm tools,
the instruments, the exclusion telemetry, the blind SBA grading tool, and the
export.

It deliberately does not contain any part of the SENSEE-I application itself.
The one point of contact is ``study/senseei_link.py``; nothing else in here may
import from or reach into the app. That boundary is what lets the app evolve
independently without breaking the trial harness.
"""

from __future__ import annotations

__all__ = ["Arm", "Phase"]

from .arms import Arm
from .phases import Phase
