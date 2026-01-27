import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.main import create_app
from app.db.models import Base
from app.db import session as db_session


@pytest.fixture(scope="session")
def test_engine():
    database_url = os.getenv("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    engine = create_engine(database_url, future=True)
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