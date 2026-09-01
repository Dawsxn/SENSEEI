"""What each arm actually does during the 40-minute intervention phase.

Two of the three arms are built here. The third, SENSEE-I, runs in the
application and is reached through ``study/senseei_link.py``.

| Arm | Module |
| --- | --- |
| Unguided LLM | ``unguided.py`` |
| Passive control | ``passive.py`` |

Both record the raw quantities the exclusion criteria of Section 4.6.3 are
derived from. Neither applies a threshold: the cutoffs are set empirically from
the pilot, and a threshold compiled into the tool could not be revised afterwards
without invalidating the data collected under the old one.
"""

from __future__ import annotations

__all__ = [
    "Conversation",
    "PassiveSession",
    "Speaker",
    "Turn",
    "UnguidedSession",
]

from .conversation import Conversation, Speaker, Turn
from .passive import PassiveSession
from .unguided import UnguidedSession
