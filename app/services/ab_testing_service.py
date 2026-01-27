from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List

from sqlalchemy.orm import Session

from app.db.models import Assignment, EventsAgg, Experiment
from app.utils.hashing import stable_hash


DEFAULT_EXPERIMENT_NAME = "hybrid_vs_popular"
DEFAULT_VARIANTS: List[str] = ["hybrid", "popular"]


def get_or_create_experiment(db: Session, name: str = DEFAULT_EXPERIMENT_NAME) -> Experiment:
    experiment = db.query(Experiment).filter(Experiment.name == name).one_or_none()
    if experiment:
        return experiment

    config: Dict[str, object] = {
        "variants": DEFAULT_VARIANTS,
        "description": "Hybrid vs popular recommender comparison",
    }
    experiment = Experiment(
        name=name,
        status="active",
        config=config,
        created_at=datetime.utcnow(),
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return experiment


def assign_user_to_experiment(db: Session, experiment: Experiment, user_id: int) -> Assignment:
    assignment = (
        db.query(Assignment)
        .filter(Assignment.user_id == user_id, Assignment.experiment_id == experiment.id)
        .one_or_none()
    )
    if assignment:
        return assignment

    variants: List[str] = experiment.config.get("variants") or DEFAULT_VARIANTS  # type: ignore[assignment]

    # Deterministic assignment using stable hashing of (experiment_name, user_id)
    key = f"{experiment.name}:{user_id}"
    hash_hex = stable_hash(key)
    bucket = int(hash_hex, 16)
    variant = variants[bucket % len(variants)]

    assignment = Assignment(
        user_id=user_id,
        experiment_id=experiment.id,
        variant=variant,
        assigned_at=datetime.utcnow(),
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def _get_or_create_events_row(
    db: Session,
    experiment: Experiment,
    variant: str,
    for_date: date | None = None,
) -> EventsAgg:
    if for_date is None:
        for_date = date.today()
    row = (
        db.query(EventsAgg)
        .filter(
            EventsAgg.date == for_date,
            EventsAgg.experiment_id == experiment.id,
            EventsAgg.variant == variant,
        )
        .one_or_none()
    )
    if row:
        return row

    row = EventsAgg(
        date=for_date,
        experiment_id=experiment.id,
        variant=variant,
        impressions=0,
        clicks=0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def log_impression(db: Session, experiment: Experiment, variant: str) -> None:
    row = _get_or_create_events_row(db, experiment, variant)
    row.impressions += 1
    db.add(row)
    db.commit()


def log_click(db: Session, experiment: Experiment, variant: str) -> None:
    row = _get_or_create_events_row(db, experiment, variant)
    row.clicks += 1
    db.add(row)
    db.commit()


def get_experiment_report(db: Session, experiment: Experiment) -> Dict[str, Dict[str, float]]:
    rows = db.query(EventsAgg).filter(EventsAgg.experiment_id == experiment.id).all()
    by_variant: Dict[str, Dict[str, float]] = {}
    for r in rows:
        stats = by_variant.setdefault(
            r.variant,
            {"impressions": 0.0, "clicks": 0.0},
        )
        stats["impressions"] += float(r.impressions)
        stats["clicks"] += float(r.clicks)

    for stats in by_variant.values():
        impressions = stats["impressions"]
        clicks = stats["clicks"]
        stats["ctr"] = clicks / impressions if impressions > 0 else 0.0

    return by_variant