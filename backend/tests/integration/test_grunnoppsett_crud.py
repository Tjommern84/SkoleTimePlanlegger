from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.db.base import Base, get_db
from app.db.models.user import User
from app.db.models.zone import Zone, ZoneMembership, ZoneRole
from app.main import app


class _FakeUser:
    id = 1
    email = "test@example.com"
    name = "Test User"


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, connection_record):  # noqa: ANN001, ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    from app.db import models  # noqa: F401

    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    session = TestingSessionLocal()
    session.add(User(id=1, google_sub="fake-sub", email=_FakeUser.email, name=_FakeUser.name))
    zone = Zone(name="Test zone", created_at=datetime.now(timezone.utc).replace(tzinfo=None))
    session.add(zone)
    session.flush()
    session.add(
        ZoneMembership(
            zone_id=zone.id,
            user_id=1,
            role=ZoneRole.OWNER,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
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
    app.dependency_overrides[get_current_user] = lambda: _FakeUser()
    test_client = TestClient(app)
    test_client.headers["X-Zone-Id"] = str(zone_id)
    yield test_client
    app.dependency_overrides.clear()


def test_school_year_update_and_cascade_delete(client):
    year = client.post("/api/school-years", json={"label": "2025/2026"}).json()

    resp = client.patch(f"/api/school-years/{year['id']}", json={"label": "2026/2027"})
    assert resp.status_code == 200
    assert resp.json()["label"] == "2026/2027"

    trinn = client.post("/api/trinn", json={"school_year_id": year["id"], "level": 8}).json()
    school_class = client.post("/api/classes", json={"trinn_id": trinn["id"], "name": "8A"}).json()
    subject = client.post(
        "/api/subjects", json={"school_year_id": year["id"], "name": "Norsk", "short_code": "NO"}
    ).json()
    group = client.get("/api/class-groups", params={"school_class_id": school_class["id"]}).json()[0]
    client.post(
        "/api/activities",
        json={
            "school_year_id": year["id"],
            "activity_type": "NORMAL",
            "duration_ticks": 2,
            "occurrences_per_week": 1,
            "legs": [{"class_group_id": group["id"], "subject_id": subject["id"], "teacher_ids": []}],
        },
    )

    # A school year with real data underneath it must still be fully
    # deletable in one action -- unlike Trinn/Class (see the restrict
    # tests below), there's no legitimate reason to keep orphaned trinn/
    # subjects/activities around once their school year is gone.
    resp = client.delete(f"/api/school-years/{year['id']}")
    assert resp.status_code == 204

    # The school year itself (and therefore everything scoped to it) is
    # gone -- these routes 404 via the zone-membership lookup rather than
    # returning empty lists, since the parent school year no longer exists.
    assert client.get(f"/api/trinn?school_year_id={year['id']}").status_code == 404
    assert client.get(f"/api/subjects?school_year_id={year['id']}").status_code == 404
    assert client.get(f"/api/activities?school_year_id={year['id']}").status_code == 404
    assert year["id"] not in [y["id"] for y in client.get("/api/school-years").json()]


def test_trinn_update_and_restrict_delete(client):
    year = client.post("/api/school-years", json={"label": "2025/2026"}).json()
    trinn = client.post("/api/trinn", json={"school_year_id": year["id"], "level": 8}).json()

    resp = client.patch(f"/api/trinn/{trinn['id']}", json={"school_year_id": year["id"], "level": 9})
    assert resp.status_code == 200
    assert resp.json()["level"] == 9

    client.post("/api/classes", json={"trinn_id": trinn["id"], "name": "9A"})

    resp = client.delete(f"/api/trinn/{trinn['id']}")
    assert resp.status_code == 409


def test_create_class_auto_creates_whole_group(client):
    year = client.post("/api/school-years", json={"label": "2025/2026"}).json()
    trinn = client.post("/api/trinn", json={"school_year_id": year["id"], "level": 8}).json()
    school_class = client.post("/api/classes", json={"trinn_id": trinn["id"], "name": "8A"}).json()

    groups = client.get("/api/class-groups", params={"school_class_id": school_class["id"]}).json()
    assert len(groups) == 1
    assert groups[0]["label"] == "whole"


def test_class_update_and_delete(client):
    year = client.post("/api/school-years", json={"label": "2025/2026"}).json()
    trinn = client.post("/api/trinn", json={"school_year_id": year["id"], "level": 8}).json()
    school_class = client.post("/api/classes", json={"trinn_id": trinn["id"], "name": "8A"}).json()

    resp = client.patch(f"/api/classes/{school_class['id']}", json={"trinn_id": trinn["id"], "name": "8B"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "8B"

    # Delete blocked while the auto-created "whole" group exists.
    resp = client.delete(f"/api/classes/{school_class['id']}")
    assert resp.status_code == 409

    groups = client.get("/api/class-groups", params={"school_class_id": school_class["id"]}).json()
    for g in groups:
        client.delete(f"/api/class-groups/{g['id']}")

    resp = client.delete(f"/api/classes/{school_class['id']}")
    assert resp.status_code == 204


def test_class_group_update_and_delete(client):
    year = client.post("/api/school-years", json={"label": "2025/2026"}).json()
    trinn = client.post("/api/trinn", json={"school_year_id": year["id"], "level": 9}).json()
    school_class = client.post("/api/classes", json={"trinn_id": trinn["id"], "name": "9A"}).json()
    group = client.post(
        "/api/class-groups", json={"school_class_id": school_class["id"], "label": "half1"}
    ).json()

    resp = client.patch(
        f"/api/class-groups/{group['id']}", json={"school_class_id": school_class["id"], "label": "half2"}
    )
    assert resp.status_code == 200
    assert resp.json()["label"] == "half2"

    resp = client.delete(f"/api/class-groups/{group['id']}")
    assert resp.status_code == 204


def test_period_update_and_delete(client):
    year = client.post("/api/school-years", json={"label": "2025/2026"}).json()
    period = client.post(
        "/api/periods",
        json={
            "school_year_id": year["id"],
            "day_of_week": "MON",
            "period_number": 1,
            "start_time": "08:30:00",
            "end_time": "09:30:00",
            "is_splittable": False,
            "is_before_lunch": True,
        },
    ).json()

    resp = client.patch(
        f"/api/periods/{period['id']}",
        json={
            "school_year_id": year["id"],
            "day_of_week": "MON",
            "period_number": 1,
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "is_splittable": True,
            "is_before_lunch": True,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["is_splittable"] is True

    resp = client.delete(f"/api/periods/{period['id']}")
    assert resp.status_code == 204


def test_duplicate_period_returns_409_not_500(client):
    year = client.post("/api/school-years", json={"label": "2025/2026"}).json()
    payload = {
        "school_year_id": year["id"],
        "day_of_week": "MON",
        "period_number": 1,
        "start_time": "08:30:00",
        "end_time": "09:30:00",
        "is_splittable": False,
        "is_before_lunch": True,
    }
    resp = client.post("/api/periods", json=payload)
    assert resp.status_code == 201

    resp = client.post("/api/periods", json=payload)
    assert resp.status_code == 409


def test_subject_update_and_delete_cascades_hour_allocations(client):
    year = client.post("/api/school-years", json={"label": "2025/2026"}).json()
    trinn = client.post("/api/trinn", json={"school_year_id": year["id"], "level": 8}).json()
    subject = client.post(
        "/api/subjects", json={"school_year_id": year["id"], "name": "Norsk", "short_code": "NO"}
    ).json()

    resp = client.patch(
        f"/api/subjects/{subject['id']}",
        json={"school_year_id": year["id"], "name": "Norsk", "short_code": "NO", "uses_hall": True},
    )
    assert resp.status_code == 200
    assert resp.json()["uses_hall"] is True

    allocation = client.post(
        "/api/subject-hour-allocations",
        json={"subject_id": subject["id"], "trinn_id": trinn["id"], "weekly_hours": 4},
    ).json()

    resp = client.patch(
        f"/api/subject-hour-allocations/{allocation['id']}",
        json={"subject_id": subject["id"], "trinn_id": trinn["id"], "weekly_hours": 5},
    )
    assert resp.status_code == 200
    assert resp.json()["weekly_hours"] == 5

    # Deleting the subject should cascade-clean its hour allocations rather
    # than being blocked or leaving orphaned rows.
    resp = client.delete(f"/api/subjects/{subject['id']}")
    assert resp.status_code == 204

    resp = client.get("/api/subject-hour-allocations", params={"subject_id": subject["id"]})
    assert resp.status_code == 404  # the subject itself is gone


def test_activity_leg_count_validation(client):
    year = client.post("/api/school-years", json={"label": "2025/2026"}).json()
    subject = client.post(
        "/api/subjects", json={"school_year_id": year["id"], "name": "Norsk", "short_code": "NO"}
    ).json()

    resp = client.post(
        "/api/activities",
        json={
            "school_year_id": year["id"],
            "activity_type": "NORMAL",
            "duration_ticks": 2,
            "occurrences_per_week": 1,
            "legs": [
                {"class_group_id": None, "subject_id": subject["id"], "teacher_ids": []},
                {"class_group_id": None, "subject_id": subject["id"], "teacher_ids": []},
            ],
        },
    )
    assert resp.status_code == 400

    resp = client.post(
        "/api/activities",
        json={
            "school_year_id": year["id"],
            "activity_type": "SPLIT_PARALLEL",
            "duration_ticks": 2,
            "occurrences_per_week": 1,
            "legs": [{"class_group_id": None, "subject_id": subject["id"], "teacher_ids": []}],
        },
    )
    assert resp.status_code == 400

    resp = client.post(
        "/api/activities",
        json={
            "school_year_id": year["id"],
            "activity_type": "TRINNFAG",
            "duration_ticks": 2,
            "occurrences_per_week": 1,
            "legs": [],
        },
    )
    assert resp.status_code == 400
