import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.db.base import Base, get_db
from app.main import app
from tests.fixtures.school_example_data import seed_school_example_data


class _FakeUser:
    email = "test@example.com"
    name = "Test User"


@pytest.fixture()
def client_with_data():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    from app.db import models  # noqa: F401

    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    seed_session = TestingSessionLocal()
    result = seed_school_example_data(seed_session)
    school_year_id = result["school_year"].id
    seed_session.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: _FakeUser()
    yield TestClient(app), school_year_id
    app.dependency_overrides.clear()


def test_solve_endpoint_persists_a_full_timetable(client_with_data):
    client, school_year_id = client_with_data

    resp = client.post("/api/solve", json={"school_year_id": school_year_id, "time_limit_seconds": 30})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("OPTIMAL", "FEASIBLE")
    assert body["infeasible_sessions"] == []
    assert body["placement_count"] > 0

    resp2 = client.get(f"/api/school-years/{school_year_id}/timetable/active")
    assert resp2.status_code == 200
    active = resp2.json()
    assert active["is_active"] is True
    assert active["solver_status"] in ("OPTIMAL", "FEASIBLE")
    assert len(active["slots"]) == body["placement_count"]


def test_second_solve_deactivates_the_first(client_with_data):
    client, school_year_id = client_with_data

    first = client.post("/api/solve", json={"school_year_id": school_year_id}).json()
    second = client.post("/api/solve", json={"school_year_id": school_year_id}).json()
    assert first["generated_timetable_id"] != second["generated_timetable_id"]

    active = client.get(f"/api/school-years/{school_year_id}/timetable/active").json()
    assert active["id"] == second["generated_timetable_id"]


def test_solve_with_variant_count_returns_distinct_equally_valid_plans(client_with_data):
    client, school_year_id = client_with_data

    resp = client.post(
        "/api/solve",
        json={"school_year_id": school_year_id, "time_limit_seconds": 30, "variant_count": 3},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["variants"]) == 3
    ids = [v["generated_timetable_id"] for v in body["variants"]]
    assert len(set(ids)) == 3  # all distinct GeneratedTimetable rows
    assert all(v["status"] in ("OPTIMAL", "FEASIBLE") for v in body["variants"])
    # Only the first variant is active by default.
    assert body["variants"][0]["is_active"] is True
    assert all(not v["is_active"] for v in body["variants"][1:])

    # Switching the active variant works.
    other_id = body["variants"][1]["generated_timetable_id"]
    resp2 = client.post(f"/api/generated-timetables/{other_id}/activate")
    assert resp2.status_code == 200
    assert resp2.json()["is_active"] is True

    active = client.get(f"/api/school-years/{school_year_id}/timetable/active").json()
    assert active["id"] == other_id
