from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from app.core.logging import get_request_id
from app.db.models import Interaction, Item, ModelVersion, User
from app.db.session import get_db
from app.schemas.stats import StatsCounts, StatsResponse

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)) -> StatsResponse:
    users_count = db.query(User).count()
    items_count = db.query(Item).count()
    interactions_count = db.query(Interaction).count()
    active_models_count = db.query(ModelVersion).filter(ModelVersion.is_active.is_(True)).count()

    counts = StatsCounts(
        users=users_count,
        items=items_count,
        interactions=interactions_count,
        active_models=active_models_count,
    )
    return StatsResponse(counts=counts, request_id=get_request_id())