"""Nothing before this file verified that two zones' data is actually
isolated from each other -- see MEMORY/the plan this implements. These
tests are the load-bearing ones for the whole multi-tenancy change.
"""

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


class _FakeUser:
    id = 1
    email = "a@example.com"
    name = "User A"


@pytest.fixture()
def two_zones():
    """User A is a member only of zone A. Zone B exists but A has no
    membership in it -- everything A does with zone B's id should 404.
    """
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    from app.db import models  # noqa: F401

    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    session = TestingSessionLocal()
    session.add(User(id=1, google_sub="sub-a", email=_FakeUser.email, name=_FakeUser.name))
    zone_a = Zone(name="Zone A", created_at=now)
    zone_b = Zone(name="Zone B", created_at=now)
    session.add_all([zone_a, zone_b])
    session.flush()
    session.add(ZoneMembership(zone_id=zone_a.id, user_id=1, role=ZoneRole.OWNER, created_at=now))
    session.commit()
    zone_a_id, zone_b_id = zone_a.id, zone_b.id
    session.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: _FakeUser()
    yield TestClient(app), zone_a_id, zone_b_id
    app.dependency_overrides.clear()


def test_member_can_use_own_zone(two_zones):
    client, zone_a_id, _ = two_zones
    resp = client.post(
        "/api/school-years", json={"label": "2025/2026"}, headers={"X-Zone-Id": str(zone_a_id)}
    )
    assert resp.status_code == 201


def test_non_member_gets_404_listing_a_zone_they_are_not_in(two_zones):
    client, _, zone_b_id = two_zones
    resp = client.get("/api/school-years", headers={"X-Zone-Id": str(zone_b_id)})
    assert resp.status_code == 404


def test_non_member_gets_404_creating_in_a_zone_they_are_not_in(two_zones):
    client, _, zone_b_id = two_zones
    resp = client.post(
        "/api/school-years", json={"label": "2025/2026"}, headers={"X-Zone-Id": str(zone_b_id)}
    )
    assert resp.status_code == 404


def test_nonexistent_zone_id_is_404_not_500(two_zones):
    client, _, _ = two_zones
    resp = client.get("/api/school-years", headers={"X-Zone-Id": "999999"})
    assert resp.status_code == 404


def test_cannot_create_activity_pointing_at_another_zones_school_year(two_zones):
    """The IDOR case the "derive zone from resource" design exists to
    close: a real member of zone A, correctly authenticated, tries to
    reference a school_year_id that belongs to zone B in a create body.
    """
    client, zone_a_id, zone_b_id = two_zones

    # Seed a school year owned by zone B directly (bypassing the API, since
    # the fake user has no membership there to create it through) --
    # mirrors how an attacker would have to have learned the id (e.g. by
    # guessing a small integer) without ever being a member of zone B.
    from app.db.models.school_year import SchoolYear

    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    school_year_b = SchoolYear(zone_id=zone_b_id, label="2099/2100")
    db.add(school_year_b)
    db.commit()
    db.refresh(school_year_b)
    school_year_b_id = school_year_b.id
    db.close()

    resp = client.post(
        "/api/activities",
        json={
            "school_year_id": school_year_b_id,
            "activity_type": "NORMAL",
            "duration_ticks": 2,
            "occurrences_per_week": 1,
            "legs": [],
        },
    )
    assert resp.status_code == 404


def test_cannot_patch_or_delete_a_trinn_in_another_zone(two_zones):
    """Same IDOR class, exercised against one of the new grunnoppsett CRUD
    routes added this session -- a real member of zone A tries to PATCH/
    DELETE a Trinn id that belongs to zone B.
    """
    client, zone_a_id, zone_b_id = two_zones

    from app.db.models.school_year import SchoolYear
    from app.db.models.trinn_class import Trinn

    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    school_year_b = SchoolYear(zone_id=zone_b_id, label="2099/2100")
    db.add(school_year_b)
    db.flush()
    trinn_b = Trinn(school_year_id=school_year_b.id, level=8)
    db.add(trinn_b)
    db.commit()
    db.refresh(trinn_b)
    trinn_b_id = trinn_b.id
    school_year_b_id = school_year_b.id
    db.close()

    resp = client.patch(f"/api/trinn/{trinn_b_id}", json={"school_year_id": school_year_b_id, "level": 9})
    assert resp.status_code == 404

    resp = client.delete(f"/api/trinn/{trinn_b_id}")
    assert resp.status_code == 404
