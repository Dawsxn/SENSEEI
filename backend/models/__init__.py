"""The schema.

Importing this module registers every table on `SQLModel.metadata`, which is
what Alembic autogenerate compares the database against. A model not imported
here is a model Alembic cannot see, so it would silently never get a migration.

No `Relationship` attributes anywhere. Under async, a lazy load raises at
attribute access rather than quietly issuing a query, so relationships would be
a trap with no current benefit; queries use explicit joins instead.
"""

from .base import TS, Entity, SoftDelete, utcnow
from .enums import STEP_ORDER, Role, SeeiStep, SessionStatus, Verdict
from .people import Class, Enrolment, User
from .readings import CoreComponent, Reading, ReadingAssignment
from .sessions import Assessment, Attempt, CriterionJudgment, Session, TutorMessage

__all__ = [
    "TS", "Entity", "SoftDelete", "utcnow",
    "STEP_ORDER", "Role", "SeeiStep", "SessionStatus", "Verdict",
    "User", "Class", "Enrolment",
    "Reading", "CoreComponent", "ReadingAssignment",
    "Session", "Attempt", "Assessment", "CriterionJudgment", "TutorMessage",
]
