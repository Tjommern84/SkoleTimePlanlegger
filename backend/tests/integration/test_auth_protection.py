from datetime import datetime, timezone
from unittest.mock import AsyncMock

from authlib.integrations.base_client.errors import OAuthError
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.google_oauth import oauth
from app.auth.session import SESSION_COOKIE_NAME, create_session_token
from app.config import settings
from app.db.base import Base, get_db
from app.db.models.user import User
from app.db.models.zone import Zone, ZoneMembership, ZoneRole
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
    user = User(google_sub="sub-123", email="lise@example.com", name="Lise")
    db.add(user)
    db.flush()
    zone = Zone(name="Lise sin sone", created_at=datetime.now(timezone.utc).replace(tzinfo=None))
    db.add(zone)
    db.flush()
    db.add(
        ZoneMembership(
            zone_id=zone.id,
            user_id=user.id,
            role=ZoneRole.OWNER,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    db.commit()
    zone_id = zone.id
    db.close()

    token = create_session_token("lise@example.com")
    client.cookies.set(SESSION_COOKIE_NAME, token)
    resp = client.post(
        "/api/school-years", json={"label": "2025/2026"}, headers={"X-Zone-Id": str(zone_id)}
    )
    assert resp.status_code == 201


def test_protected_route_rejects_missing_zone_header(client_no_auth_override):
    client, SessionLocal = client_no_auth_override
    db = SessionLocal()
    db.add(User(google_sub="sub-123", email="lise@example.com", name="Lise"))
    db.commit()
    db.close()

    token = create_session_token("lise@example.com")
    client.cookies.set(SESSION_COOKIE_NAME, token)
    resp = client.post("/api/school-years", json={"label": "2025/2026"})
    assert resp.status_code == 400


def test_health_endpoint_does_not_require_auth(client_no_auth_override):
    client, _ = client_no_auth_override
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_callback_with_stale_code_redirects_instead_of_500(client_no_auth_override, monkeypatch):
    """A reused/expired Google authorization code (e.g. reloading the
    callback URL, a "request desktop site" refresh, or navigating back
    through browser history) makes Authlib raise OAuthError. This must
    bounce back to the frontend, not leak a raw 500.
    """
    client, _ = client_no_auth_override
    monkeypatch.setattr(
        oauth.google, "authorize_access_token", AsyncMock(side_effect=OAuthError("invalid_grant"))
    )

    resp = client.get("/auth/callback", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == settings.frontend_url
