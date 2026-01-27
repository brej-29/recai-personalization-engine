from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.ab_testing_service import get_or_create_experiment, assign_user_to_experiment


def test_deterministic_assignment(db: Session) -> None:
    experiment = get_or_create_experiment(db)
    assignment1 = assign_user_to_experiment(db, experiment, user_id=123)
    assignment2 = assign_user_to_experiment(db, experiment, user_id=123)

    assert assignment1.variant in {"hybrid", "popular"}
    assert assignment1.variant == assignment2.variant


def test_metrics_endpoint(client: TestClient) -> None:
    resp = client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "recai_request_count" in text
    assert "recai_latency_ms_bucket" in text