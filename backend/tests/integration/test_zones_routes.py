from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.db.base import Base, get_db
from app.db.models.user import User
from app.db.models.zone import Zone, ZoneMembership, ZoneRole
from app.main import app

_OWNER = "owner@example.com"
_MEMBER = "member@example.com"


class _AsUser:
    def __init__(self, id_: int, email: str):
        self.id = id_
        self.email = email
        self.name = email.split("@")[0]


@pytest.fixture()
def zone_with_owner_and_member():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    from app.db import models  # noqa: F401

    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    session = TestingSessionLocal()
    session.add(User(id=1, google_sub="sub-owner", email=_OWNER, name="Owner"))
    session.add(User(id=2, google_sub="sub-member", email=_MEMBER, name="Member"))
    zone = Zone(name="Shared zone", created_at=now)
    session.add(zone)
    session.flush()
    session.add(ZoneMembership(zone_id=zone.id, user_id=1, role=ZoneRole.OWNER, created_at=now))
    session.add(ZoneMembership(zone_id=zone.id, user_id=2, role=ZoneRole.MEMBER, created_at=now))
    session.commit()
    zone_id = zone.id
    session.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestingSessionLocal, zone_id
    app.dependency_overrides.clear()


def _client_as(user_id: int, email: str, zone_id: int) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: _AsUser(user_id, email)
    client = TestClient(app)
    client.headers["X-Zone-Id"] = str(zone_id)
    return client


def test_owner_can_invite_and_list_members(zone_with_owner_and_member):
    _, zone_id = zone_with_owner_and_member
    client = _client_as(1, _OWNER, zone_id)

    resp = client.get("/api/zones/current/members")
    assert resp.status_code == 200
    assert {m["email"] for m in resp.json()} == {_OWNER, _MEMBER}

    resp = client.post("/api/zones/current/invitations", json={"email": "new@example.com"})
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"


def test_member_cannot_invite_or_remove(zone_with_owner_and_member):
    _, zone_id = zone_with_owner_and_member
    client = _client_as(2, _MEMBER, zone_id)

    resp = client.post("/api/zones/current/invitations", json={"email": "new@example.com"})
    assert resp.status_code == 403

    resp = client.delete("/api/zones/current/members/1")
    assert resp.status_code == 403


def test_cannot_invite_someone_already_a_member(zone_with_owner_and_member):
    _, zone_id = zone_with_owner_and_member
    client = _client_as(1, _OWNER, zone_id)

    resp = client.post("/api/zones/current/invitations", json={"email": _MEMBER})
    assert resp.status_code == 400


def test_duplicate_pending_invitation_is_rejected(zone_with_owner_and_member):
    _, zone_id = zone_with_owner_and_member
    client = _client_as(1, _OWNER, zone_id)

    first = client.post("/api/zones/current/invitations", json={"email": "new@example.com"})
    assert first.status_code == 201
    second = client.post("/api/zones/current/invitations", json={"email": "new@example.com"})
    assert second.status_code == 409


def test_owner_can_remove_a_member(zone_with_owner_and_member):
    _, zone_id = zone_with_owner_and_member
    client = _client_as(1, _OWNER, zone_id)

    resp = client.delete("/api/zones/current/members/2")
    assert resp.status_code == 204

    resp = client.get("/api/zones/current/members")
    assert {m["email"] for m in resp.json()} == {_OWNER}


def test_cannot_remove_the_last_remaining_owner(zone_with_owner_and_member):
    _, zone_id = zone_with_owner_and_member
    client = _client_as(1, _OWNER, zone_id)

    resp = client.delete("/api/zones/current/members/1")
    assert resp.status_code == 400
