from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.logging import get_request_id
from app.core.exceptions import ValidationAppError
from app.db.models import Item, ModelVersion, Experiment
from app.db.session import get_db
from app.schemas.admin import (
    ModelVersionResponse,
    TrainResponse,
    TrackEventRequest,
    TrackEventResponse,
    AdminCreateItemRequest,
    AdminCreateItemResponse,
    ExperimentCreateResponse,
    ExperimentReportResponse,
    ExperimentReportVariant,
    ExperimentSummary,
)
from app.services.cache_service import update_popularity_and_trending_counters
from app.services.interaction_service import track_interaction
from app.services.ab_testing_service import (
    get_or_create_experiment,
    assign_user_to_experiment,
    log_click,
    get_experiment_report,
)
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


@admin_router.post("/items", response_model=AdminCreateItemResponse)
def create_item(payload: AdminCreateItemRequest, db: Session = Depends(get_db)) -> AdminCreateItemResponse:
    genres_str = "|".join(payload.genres) if payload.genres else None
    text = payload.text or payload.title
    item = Item(
        id=payload.explicit_id,
        title=payload.title,
        genres=genres_str,
        text=text,
        metadata=payload.metadata,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return AdminCreateItemResponse(
        id=item.id,
        title=item.title,
        genres=item.genres,
        text=item.text,
        metadata=item.metadata,
        request_id=get_request_id(),
    )


@admin_router.post("/experiments/create", response_model=ExperimentCreateResponse)
def create_experiment(db: Session = Depends(get_db)) -> ExperimentCreateResponse:
    experiment = get_or_create_experiment(db)
    summary = ExperimentSummary(
        name=experiment.name,
        status=experiment.status,
        created_at=experiment.created_at,
        config=experiment.config,
    )
    return ExperimentCreateResponse(experiment=summary, request_id=get_request_id())


@admin_router.get("/experiments", response_model=list[ExperimentSummary])
def list_experiments(db: Session = Depends(get_db)) -> list[ExperimentSummary]:
    experiments = db.query(Experiment).order_by(Experiment.created_at.desc()).all()
    return [
        ExperimentSummary(
            name=e.name,
            status=e.status,
            created_at=e.created_at,
            config=e.config,
        )
        for e in experiments
    ]


@admin_router.get("/experiments/{name}/report", response_model=ExperimentReportResponse)
def experiment_report(name: str, db: Session = Depends(get_db)) -> ExperimentReportResponse:
    experiment = get_or_create_experiment(db, name=name)
    stats = get_experiment_report(db, experiment)
    variants: list[ExperimentReportVariant] = []
    for variant_name, values in stats.items():
        variants.append(
            ExperimentReportVariant(
                variant=variant_name,
                impressions=int(values.get("impressions", 0)),
                clicks=int(values.get("clicks", 0)),
                ctr=float(values.get("ctr", 0.0)),
            )
        )
    return ExperimentReportResponse(
        name=experiment.name,
        status=experiment.status,
        variants=variants,
        request_id=get_request_id(),
    )


@tracking_router.post("/track", response_model=TrackEventResponse)
def track_event(payload: TrackEventRequest, db: Session = Depends(get_db)) -> TrackEventResponse:
    # Persist interaction
    track_interaction(
        db=db,
        user_id=payload.user_id,
        item_id=payload.item_id,
        event_type=payload.event_type,
        rating=payload.rating,
        ts=payload.ts,
    )

    # Update Redis counters for popularity / trending
    item = db.get(Item, payload.item_id)
    genres: list[str] = []
    if item and item.genres:
        genres = [g.strip() for g in item.genres.split("|") if g.strip()]
    update_popularity_and_trending_counters(
        item_id=payload.item_id,
        genres=genres,
        weight=1.0,
        ts=payload.ts,
    )

    # A/B testing click tracking
    if payload.event_type == "click":
        experiment = get_or_create_experiment(db)
        assignment = assign_user_to_experiment(db, experiment, user_id=payload.user_id)
        if assignment.variant in {"hybrid", "popular"}:
            log_click(db, experiment, assignment.variant)

    return TrackEventResponse(status="ok", request_id=get_request_id())