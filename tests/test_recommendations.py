from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Interaction, Item, User


def seed_basic_data(db: Session) -> None:
    user = User(id=1)
    item1 = Item(id=1, title="Item 1", genres="Action", text="Action movie")
    item2 = Item(id=2, title="Item 2", genres="Drama", text="Drama movie")
    db.add_all([user, item1, item2])
    db.commit()

    inter = Interaction(
        user_id=1,
        item_id=1,
        event_type="rate",
        rating=5.0,
        ts=datetime.utcnow(),
    )
    db.add(inter)
    db.commit()


def test_popular_recommendations(client: TestClient, db: Session) -> None:
    seed_basic_data(db)
    resp = client.get("/v1/recommendations", params={"user_id": 1, "strategy": "popular"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["strategy"] == "popular"
    assert "items" in data
    assert isinstance(data["items"], list)


def test_hybrid_recommendations_fallback_to_popular(client: TestClient, db: Session) -> None:
    """Hybrid should gracefully fall back to popularity when models are not trained."""
    seed_basic_data(db)
    resp = client.get("/v1/recommendations", params={"user_id": 1, "strategy": "hybrid"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == 1
    assert data["strategy"] == "hybrid"
    assert "items" in data
    assert isinstance(data["items"], list)
    # Reasons list should be present for hybrid items
    if data["items"]:
        item = data["items"][0]
        assert "reasons" in item