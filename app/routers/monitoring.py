from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.metrics import export_metrics_text
from app.db.models import EventsAgg, ModelVersion
from app.db.session import get_db

router = APIRouter(tags=["monitoring"])

templates = Jinja2Templates(directory="app/templates")


@router.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    """Prometheus-style metrics endpoint."""
    return export_metrics_text()


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    # Basic counts
    users_count = db.execute("SELECT COUNT(*) FROM users").scalar() or 0
    items_count = db.execute("SELECT COUNT(*) FROM items").scalar() or 0
    interactions_count = db.execute("SELECT COUNT(*) FROM interactions").scalar() or 0

    # Active models
    active_models = (
        db.query(ModelVersion)
        .filter(ModelVersion.is_active.is_(True))
        .order_by(ModelVersion.trained_at.desc())
        .all()
    )

    # Simple A/B stats for hybrid_vs_popular
    ab_stats = (
        db.query(
            EventsAgg.variant,
            func.sum(EventsAgg.impressions).label("impressions"),
            func.sum(EventsAgg.clicks).label("clicks"),
        )
        .group_by(EventsAgg.variant)
        .all()
    )
    variants = []
    for row in ab_stats:
        impressions = int(row.impressions or 0)
        clicks = int(row.clicks or 0)
        ctr = (clicks / impressions) if impressions > 0 else 0.0
        variants.append({"variant": row.variant, "impressions": impressions, "clicks": clicks, "ctr": ctr})

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "users_count": users_count,
            "items_count": items_count,
            "interactions_count": interactions_count,
            "active_models": active_models,
            "ab_variants": variants,
        },
    )