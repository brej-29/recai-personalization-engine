from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.logging import get_request_id
from app.core.exceptions import ValidationAppError
from app.db.models import ModelVersion
from app.db.session import get_db
from app.schemas.admin import ModelVersionResponse, TrainResponse, TrackEventRequest, TrackEventResponse
from app.services.interaction_service import track_interaction
from app.training.train import train_content_model, train_mf_model

admin_router = APIRouter(prefix="/admin", tags=["admin"])
tracking_router = APIRouter(tags=["tracking"])


@admin_router.get("/models", response_model=list[ModelVersionResponse])
def list_models(db: Session = Depends(get_db)) -> list[ModelVersionResponse]:
    models = db.query(ModelVersion).order_by(ModelVersion.trained_at.desc()).all()
    return [
        ModelVersionResponse(
            id=m.id,
            name=m.name,
            version=m.version,
            trained_at=m.trained_at,
            metrics=m.metrics,
            path=m.path,
            is_active=m.is_active,
        )
        for m in models
    ]


@admin_router.post("/train", response_model=TrainResponse)
def train(
    model: str = Query(..., pattern="^(content|mf)$", description="Model to train: content | mf"),
    db: Session = Depends(get_db),
) -> TrainResponse:
    if model == "content":
        result = train_content_model(db)
    elif model == "mf":
        result = train_mf_model(db)
    else:  # pragma: no cover
        raise ValidationAppError(message="Unsupported model", details={"model": model})

    if not result.success:
        raise HTTPException(status_code=500, detail=result.message)

    return TrainResponse(
        model=model,
        status="ok",
        details={
            "version": result.version,
            "metrics": result.metrics,
            "path": result.path,
        },
        request_id=get_request_id(),
    )


@tracking_router.post("/track", response_model=TrackEventResponse)
def track_event(payload: TrackEventRequest, db: Session = Depends(get_db)) -> TrackEventResponse:
    track_interaction(
        db=db,
        user_id=payload.user_id,
        item_id=payload.item_id,
        event_type=payload.event_type,
        rating=payload.rating,
        ts=payload.ts,
    )
    return TrackEventResponse(status="ok", request_id=get_request_id())