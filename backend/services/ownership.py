"""Whose classes, readings and batches an instructor account can see and change.

Normally an instructor's own: each teacher has their own classes. On the trial
instance the research team runs one study together, so every team account sees
and manages all of them, and any of them can void a slip or close a batch on the
day (docs/context/trial.md). The grader never reaches these queries.
"""

from __future__ import annotations

import uuid

from sqlalchemy import true
from sqlalchemy.sql.elements import ColumnElement

from ..settings import get_settings


def owned_by(column, instructor_id: uuid.UUID) -> ColumnElement[bool]:
    """The ownership condition for `column` (an instructor id column): a match
    on this instructor, or no condition at all in trial mode."""
    if get_settings().trial_mode:
        return true()
    return column == instructor_id
