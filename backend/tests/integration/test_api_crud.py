import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.db.base import Base, get_db
from app.main import app


class _FakeUser:
    email = "test@example.com"
    name = "Test User"


@pytest.fixture()
def client():
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
    app.dependency_overrides[get_current_user] = lambda: _FakeUser()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_school_year_and_subject_crud_roundtrip(client):
    resp = client.post("/api/school-years", json={"label": "2025/2026"})
    assert resp.status_code == 201
    school_year_id = resp.json()["id"]

    resp = client.post(
        "/api/subjects",
        json={
            "school_year_id": school_year_id,
            "name": "Norsk",
            "short_code": "NO",
            "is_trinnfag": False,
            "is_krov": False,
            "uses_hall": False,
        },
    )
    assert resp.status_code == 201
    subject = resp.json()
    assert subject["short_code"] == "NO"

    resp = client.get("/api/subjects", params={"school_year_id": school_year_id})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_teacher_update_and_unavailability_roundtrip(client):
    teacher_id = client.post("/api/teachers", json={"initials": "GB", "full_name": "GB"}).json()["id"]

    resp = client.patch(f"/api/teachers/{teacher_id}", json={"initials": "GB", "full_name": "Grete Berg"})
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Grete Berg"

    school_year_id = client.post("/api/school-years", json={"label": "2025/2026"}).json()["id"]
    resp = client.post(
        "/api/teacher-unavailabilities",
        json={
            "teacher_id": teacher_id,
            "school_year_id": school_year_id,
            "day_of_week": "MON",
            "start_period": 1,
            "end_period": 3,
        },
    )
    assert resp.status_code == 201
    unavailability_id = resp.json()["id"]

    resp = client.get("/api/teacher-unavailabilities", params={"teacher_id": teacher_id})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = client.delete(f"/api/teacher-unavailabilities/{unavailability_id}")
    assert resp.status_code == 204
    resp = client.get("/api/teacher-unavailabilities", params={"teacher_id": teacher_id})
    assert len(resp.json()) == 0


def test_teacher_subject_qualification_roundtrip(client):
    school_year_id = client.post("/api/school-years", json={"label": "2025/2026"}).json()["id"]
    subject_id = client.post(
        "/api/subjects",
        json={"school_year_id": school_year_id, "name": "Norsk", "short_code": "NO"},
    ).json()["id"]
    teacher_id = client.post("/api/teachers", json={"initials": "GB", "full_name": "GB"}).json()["id"]

    resp = client.post(
        "/api/teacher-subject-qualifications",
        json={"teacher_id": teacher_id, "subject_id": subject_id, "weekly_hours": 4},
    )
    assert resp.status_code == 201
    qualification_id = resp.json()["id"]

    resp = client.patch(f"/api/teacher-subject-qualifications/{qualification_id}", json={"weekly_hours": 6})
    assert resp.status_code == 200
    assert resp.json()["weekly_hours"] == 6

    resp = client.get("/api/teacher-subject-qualifications", params={"teacher_id": teacher_id})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = client.delete(f"/api/teacher-subject-qualifications/{qualification_id}")
    assert resp.status_code == 204
    resp = client.get("/api/teacher-subject-qualifications", params={"teacher_id": teacher_id})
    assert len(resp.json()) == 0


def test_activity_with_split_legs_roundtrip(client):
    school_year_id = client.post("/api/school-years", json={"label": "2025/2026"}).json()["id"]
    trinn_id = client.post("/api/trinn", json={"school_year_id": school_year_id, "level": 9}).json()["id"]
    class_id = client.post("/api/classes", json={"trinn_id": trinn_id, "name": "9A"}).json()["id"]
    half1 = client.post("/api/class-groups", json={"school_class_id": class_id, "label": "half1"}).json()["id"]
    half2 = client.post("/api/class-groups", json={"school_class_id": class_id, "label": "half2"}).json()["id"]

    mh = client.post(
        "/api/subjects",
        json={"school_year_id": school_year_id, "name": "Mat og helse", "short_code": "MH"},
    ).json()["id"]
    nat = client.post(
        "/api/subjects",
        json={"school_year_id": school_year_id, "name": "Naturfag", "short_code": "NAT"},
    ).json()["id"]

    bts = client.post("/api/teachers", json={"initials": "BTS", "full_name": "BTS"}).json()["id"]
    ehk = client.post("/api/teachers", json={"initials": "EHK", "full_name": "EHK"}).json()["id"]

    resp = client.post(
        "/api/activities",
        json={
            "school_year_id": school_year_id,
            "activity_type": "SPLIT_PARALLEL",
            "duration_ticks": 2,
            "occurrences_per_week": 2,
            "legs": [
                {"class_group_id": half1, "subject_id": mh, "teacher_ids": [bts]},
                {"class_group_id": half2, "subject_id": nat, "teacher_ids": [ehk]},
            ],
        },
    )
    assert resp.status_code == 201
    activity = resp.json()
    assert len(activity["legs"]) == 2
    assert {leg["subject_id"] for leg in activity["legs"]} == {mh, nat}

    resp = client.get("/api/activities", params={"school_year_id": school_year_id})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
