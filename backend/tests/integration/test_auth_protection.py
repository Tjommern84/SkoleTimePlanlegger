import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.session import SESSION_COOKIE_NAME, create_session_token
from app.db.base import Base, get_db
from app.db.models.user import User
from app.main import app


@pytest.fixture()
def client_no_auth_override():
    """Deliberately does NOT override get_current_user -- exercises the
    real session-cookie auth path.
    """
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    from app.db import models  # noqa: F401

    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), TestingSessionLocal
    app.dependency_overrides.clear()


def test_protected_route_rejects_missing_cookie(client_no_auth_override):
    client, _ = client_no_auth_override
    resp = client.post("/api/school-years", json={"label": "2025/2026"})
    assert resp.status_code == 401


def test_protected_route_rejects_unknown_email(client_no_auth_override):
    client, _ = client_no_auth_override
    token = create_session_token("someone-not-in-the-db@example.com")
    client.cookies.set(SESSION_COOKIE_NAME, token)
    resp = client.post("/api/school-years", json={"label": "2025/2026"})
    assert resp.status_code == 401


def test_protected_route_accepts_valid_session_for_known_user(client_no_auth_override):
    client, SessionLocal = client_no_auth_override
    db = SessionLocal()
    db.add(User(google_sub="sub-123", email="lise@example.com", name="Lise"))
    db.commit()
    db.close()

    token = create_session_token("lise@example.com")
    client.cookies.set(SESSION_COOKIE_NAME, token)
    resp = client.post("/api/school-years", json={"label": "2025/2026"})
    assert resp.status_code == 201


def test_health_endpoint_does_not_require_auth(client_no_auth_override):
    client, _ = client_no_auth_override
    resp = client.get("/api/health")
    assert resp.status_code == 200
