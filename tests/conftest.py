import os
from typing import Generator

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.db.models import Base
from app.db import session as db_session


@pytest.fixture(scope="session")
def test_engine():
    database_url = os.getenv("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")

    engine_kwargs = {"future": True}
    connect_args: dict = {}

    # For SQLite, especially in-memory, ensure a single shared connection that
    # can be used across threads (FastAPI TestClient runs handlers in threads).
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if ":memory:" in database_url:
            engine_kwargs["poolclass"] = StaticPool

    engine = create_engine(database_url, connect_args=connect_args, **engine_kwargs)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def SessionTesting(test_engine) -> sessionmaker:
    return sessionmaker(bind=test_engine, class_=Session, autoflush=False, autocommit=False)


@pytest.fixture(scope="function")
def db(SessionTesting) -> Generator[Session, None, None]:
    session = SessionTesting()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db, monkeypatch) -> TestClient:
    # Override SessionLocal used by the app with the testing sessionmaker
    db_session.SessionLocal = sessionmaker(
        bind=db.get_bind(), class_=Session, autoflush=False, autocommit=False
    )

    app = create_app()
    with TestClient(app) as c:
        yield c