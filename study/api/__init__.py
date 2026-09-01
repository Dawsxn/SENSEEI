"""The running trial: proctor console and participant screens.

Start it with::

    python -m uvicorn study.api.app:app --reload

Then open http://127.0.0.1:8000 for the proctor console. Check someone in and it
hands you their participant link.
"""

from __future__ import annotations

__all__ = ["create_app"]

from .app import create_app
