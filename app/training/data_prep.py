from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import Interaction, Item


def load_interactions(db: Session) -> pd.DataFrame:
    """Load interactions from the database into a DataFrame."""
    rows = (
        db.query(
            Interaction.user_id,
            Interaction.item_id,
            Interaction.event_type,
            Interaction.rating,
            Interaction.ts,
        )
        .order_by(Interaction.ts.asc())
        .all()
    )
    return pd.DataFrame(rows, columns=["user_id", "item_id", "event_type", "rating", "ts"])


def load_items(db: Session) -> pd.DataFrame:
    rows = db.query(Item.id, Item.title, Item.genres, Item.text).all()
    return pd.DataFrame(rows, columns=["id", "title", "genres", "text"])


def build_implicit_matrix(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build implicit feedback matrix from interactions.

    Returns
    -------
    user_ids : np.ndarray
    item_ids : np.ndarray
    data : np.ndarray
    """
    # Treat any interaction as implicit feedback of 1.0, optionally weighted by event_type.
    weights = {
        "view": 1.0,
        "click": 2.0,
        "rate": 3.0,
    }
    df = df.copy()
    df["weight"] = df["event_type"].map(weights).fillna(1.0)
    grouped = df.groupby(["user_id", "item_id"])["weight"].sum().reset_index()

    user_ids = grouped["user_id"].to_numpy(dtype=np.int64)
    item_ids = grouped["item_id"].to_numpy(dtype=np.int64)
    data = grouped["weight"].to_numpy(dtype=np.float32)
    return user_ids, item_ids, data