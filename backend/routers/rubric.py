"""The rubric endpoint.

One read, for the panel the student opens from the session's top bar. It is not
scoped to a session: the rubric is the same for everyone grading against this
deployment, and the version is a setting rather than something a request may
choose.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_current_user
from ..models import User
from ..schemas import RubricOut
from ..services import rubric_service

router = APIRouter(tags=["rubric"])


@router.get("/rubric", response_model=RubricOut)
async def get_rubric(user: User = Depends(get_current_user)) -> RubricOut:
    """Every step's criteria and what each one asks for, as the rubric words it."""
    return RubricOut(**rubric_service.pinned_rubric())
