from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.logging import get_request_id
from app.db.models import User
from app.db.session import get_db
from app.schemas.users import UserOnboardRequest, UserOnboardResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/onboard", response_model=UserOnboardResponse)
def onboard_user(payload: UserOnboardRequest, db: Session = Depends(get_db)) -> UserOnboardResponse:
    user = db.get(User, payload.user_id)
    if not user:
        user = User(id=payload.user_id)
        db.add(user)
        db.flush()

    attributes = dict(user.attributes or {})
    if payload.preferred_genres is not None:
        attributes["preferred_genres"] = payload.preferred_genres
    if payload.preferred_keywords is not None:
        attributes["preferred_keywords"] = payload.preferred_keywords
    user.attributes = attributes

    db.add(user)
    db.commit()

    return UserOnboardResponse(
        user_id=user.id,
        status="ok",
        request_id=get_request_id(),
    )