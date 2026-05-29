import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

# Register JSONB as JSON for SQLite compatibility (once at import time)
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from civicint.api.app import create_app
from civicint.api.deps import get_db
from civicint.models import Base

SQLiteTypeCompiler.visit_JSONB = SQLiteTypeCompiler.visit_JSON


@pytest.fixture
def engine():
    e = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(e)
    return e


@pytest.fixture
def db_session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)
