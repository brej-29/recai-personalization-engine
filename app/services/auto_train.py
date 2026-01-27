from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.model_registry import get_active_model_version
from app.training.train import train_content_model, train_mf_model

logger = logging.getLogger(__name__)


def _artifact_missing(db: Session, model_name: str, artifact_dir: Path) -> bool:
    """Return True if the active model version is missing or its artifact file is absent."""
    model_version = get_active_model_version(db, model_name)
    if model_version is None:
        logger.info("Auto-train: no active model version found for '%s'.", model_name)
        return True

    raw_path = Path(model_version.path)
    # If path is relative, resolve it under the configured artifact_dir if needed.
    candidates = [raw_path]
    if not raw_path.is_absolute():
        candidates.append(artifact_dir / raw_path.name)

    for candidate in candidates:
        if candidate.exists():
            logger.info(
                "Auto-train: found existing artifact for '%s' at %s.",
                model_name,
                candidate,
            )
            return False

    logger.info(
        "Auto-train: artifact for '%s' is missing (tried: %s).",
        model_name,
        ", ".join(str(c) for c in candidates),
    )
    return True


def ensure_models_trained_if_missing() -> None:
    """Ensure core models are trained when AUTO_TRAIN_ON_BOOT is enabled.

    - If AUTO_TRAIN_ON_BOOT is false, this is a no-op.
    - If enabled, checks DB + filesystem for:
        * content_tfidf
        * mf_als
      and trains any missing models.
    - Errors are logged but do not prevent app startup; the API will still
      serve popular-based recommendations as a fallback.
    """
    settings = get_settings()
    if not settings.auto_train_on_boot:
        # Keep noise low in local dev where this is typically disabled.
        logger.info("AUTO_TRAIN_ON_BOOT is disabled; skipping automatic model training.")
        return

    artifact_dir = settings.artifact_dir
    artifact_dir.mkdir(parents=True, exist_ok=True)

    with SessionLocal() as db:
        # Content-based TF-IDF model
        if _artifact_missing(db, "content_tfidf", artifact_dir):
            try:
                logger.info("Auto-train: training 'content_tfidf' model on startup...")
                result = train_content_model(db)
                if result.success:
                    logger.info(
                        "Auto-train: content_tfidf training complete (version=%s).",
                        result.version,
                    )
                else:
                    logger.warning(
                        "Auto-train: content_tfidf training reported failure: %s",
                        result.message,
                    )
            except Exception:
                logger.exception(
                    "Auto-train: unexpected error while training 'content_tfidf'; "
                    "continuing startup with popular fallback."
                )

        # Matrix factorization (ALS) model
        if _artifact_missing(db, "mf_als", artifact_dir):
            try:
                logger.info("Auto-train: training 'mf_als' model on startup...")
                result = train_mf_model(db)
                if result.success:
                    logger.info(
                        "Auto-train: mf_als training complete (version=%s).",
                        result.version,
                    )
                else:
                    logger.warning(
                        "Auto-train: mf_als training reported failure: %s",
                        result.message,
                    )
            except Exception:
                logger.exception(
                    "Auto-train: unexpected error while training 'mf_als'; "
                    "continuing startup with popular fallback."
                )