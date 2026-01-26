from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Interaction, Item, User


def get_or_create_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        user = User(id=user_id)  # allow external IDs
        db.add(user)
        db.flush()
    return user


def get_or_create_item(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        item = Item(id=item_id, title=f"Item {item_id}")
        db.add(item)
        db.flush()
    return item


def track_interaction(
    db: Session,
    *,
    user_id: int,
    item_id: int,
    event_type: str,
    rating: Optional[float] = None,
    ts: Optional[datetime] = None,
) -> Interaction:
    user = get_or_create_user(db, user_id)
    item = get_or_create_item(db, item_id)

    interaction = Interaction(
        user_id=user.id,
        item_id=item.id,
        event_type=event_type,
        rating=rating,
        ts=ts or datetime.utcnow(),
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction