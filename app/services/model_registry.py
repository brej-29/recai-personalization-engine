from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.models import ModelVersion


@dataclass
class TrainingResult:
    success: bool
    message: str
    version: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    path: Optional[str] = None


def register_model_version(
    db: Session,
    *,
    name: str,
    metrics: Optional[Dict[str, Any]],
    artifact_path: Path,
) -> Tuple[ModelVersion, str]:
    """Register a new model version and mark it active; deactivate prior ones."""
    version = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    # Deactivate previous versions
    db.query(ModelVersion).filter(
        and_(ModelVersion.name == name, ModelVersion.is_active.is_(True))
    ).update({"is_active": False})

    mv = ModelVersion(
        name=name,
        version=version,
        trained_at=datetime.utcnow(),
        metrics=metrics,
        path=str(artifact_path),
        is_active=True,
    )
    db.add(mv)
    db.commit()
    db.refresh(mv)
    return mv, version


def get_active_model_version(db: Session, name: str) -> Optional[ModelVersion]:
    return (
        db.query(ModelVersion)
        .filter(ModelVersion.name == name, ModelVersion.is_active.is_(True))
        .order_by(ModelVersion.trained_at.desc())
        .first()
    )