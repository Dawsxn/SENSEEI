"""The trial's five surveys, as versioned content rather than as code.

Demographics, the pre-test, post-test Part A, the SBA, and the SUS live as YAML
in ``content/`` and are rendered by one generic renderer. That is what lets the
faculty content-validity review of Section 4.6.4 read exactly what the tool
serves, and what makes the pre-test / post-test pairing a declared fact rather
than something buried in markup.

Generate the review document with::

    python -m study.instruments.review > review.html
"""

from __future__ import annotations

__all__ = [
    "Instrument",
    "InstrumentError",
    "InstrumentResult",
    "Item",
    "ItemType",
    "load_all",
    "load_instrument",
    "readiness",
    "score",
]

from .loader import load_all, load_instrument, readiness
from .schema import Instrument, InstrumentError, Item, ItemType
from .scoring import InstrumentResult, score
