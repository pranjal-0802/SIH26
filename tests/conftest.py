import os
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Ensure DEMO_MODE is true for tests
os.environ["DEMO_MODE"] = "true"

TEST_DB_PATH = Path(__file__).resolve().parent.parent / "test_prismarine.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

# Import models first to register with Base
import app.models
import app.database
from app.database import Base, get_db
from app.scripts.seed_data import seed_database
from app.main import app as fastapi_app

# Dedicated test engine and session factory
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Rebind app.database so endpoints, services, and tests use the dedicated test database
app.database.engine = test_engine
app.database.SessionLocal = TestSessionLocal

# FastAPI dependency override
def override_get_db():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()

fastapi_app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Session-scoped fixture that sets up an isolated test database.
    Guarantees that tables and seed data exist even on a clean clone without prismarine.db.
    """
    # Clean up any stale test database
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass

    # Create tables and seed data on test engine
    Base.metadata.create_all(bind=test_engine)
    seed_database(bind_engine=test_engine, session_factory=TestSessionLocal)

    yield

    # Teardown test database after test session
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass


@pytest.fixture(scope="session")
def client(setup_test_database):
    """
    Yields a TestClient managed via a context manager to ensure
    FastAPI lifespan hooks execute properly.
    """
    with TestClient(fastapi_app) as test_client:
        yield test_client


@pytest.fixture
def db():
    """
    Provides a database session bound to the isolated test database.
    """
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
