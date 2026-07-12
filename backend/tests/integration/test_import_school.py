import copy
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


_PERIODS = [
    {
        "day_of_week": day,
        "period_number": n,
        "start_time": f"{7 + n:02d}:00:00",
        "end_time": f"{8 + n:02d}:00:00",
        "is_splittable": False,
        "is_before_lunch": True,
    }
    for day in ("MON", "TUE", "WED", "THU", "FRI")
    for n in range(1, 5)
]


def _valid_payload(label: str = "2030/2031") -> dict:
    return {
        "school_year_label": label,
        "periods": _PERIODS,
        "trinn": [
            {"level": 8, "classes": [{"name": "8A"}]},
            {
                "level": 9,
                "classes": [
                    {"name": "9A", "extra_groups": ["half1", "half2"]},
                    {"name": "9B"},
                ],
            },
        ],
        "teachers": [
            {"initials": "AB", "full_name": "A B"},
            {"initials": "CD", "full_name": "C D"},
            {"initials": "EF", "full_name": "E F"},
            {"initials": "GH", "full_name": "G H"},
        ],
        "subjects": [
            {"short_code": "MA", "name": "Matematikk", "hour_allocations": [{"trinn_level": 8, "weekly_hours": 3}]},
            {"short_code": "MH", "name": "Mat og helse", "hour_allocations": [{"trinn_level": 9, "weekly_hours": 2}]},
            {"short_code": "NAT", "name": "Naturfag", "hour_allocations": [{"trinn_level": 9, "weekly_hours": 2}]},
            {
                "short_code": "VALG",
                "name": "Valgfag",
                "is_trinnfag": True,
                "uses_hall": True,
                "hour_allocations": [{"trinn_level": 9, "weekly_hours": 1.5}],
            },
        ],
        "activities": [
            {
                "activity_type": "NORMAL",
                "duration_minutes": 60,
                "occurrences_per_week": 3,
                "notes": "8A Matte",
                "legs": [{"class_ref": "8A", "subject_code": "MA", "teacher_initials": ["AB"]}],
            },
            {
                "activity_type": "SPLIT_PARALLEL",
                "duration_minutes": 60,
                "occurrences_per_week": 2,
                "notes": "9A delt Mat&Helse/Naturfag",
                "legs": [
                    {"class_ref": "9A:half1", "subject_code": "MH", "teacher_initials": ["CD"]},
                    {"class_ref": "9A:half2", "subject_code": "NAT", "teacher_initials": ["EF"]},
                ],
            },
            {
                "activity_type": "TRINNFAG",
                "duration_minutes": 60,
                "occurrences_per_week": 1,
                "notes": "9. trinn valgfag",
                "legs": [
                    {"class_ref": "9A", "subject_code": "VALG", "teacher_initials": ["GH"]},
                    {"class_ref": "9B", "subject_code": "VALG", "teacher_initials": ["AB"]},
                    {"class_ref": None, "subject_code": "VALG", "teacher_initials": ["CD"]},
                ],
            },
        ],
    }


def test_full_import_happy_path(client):
    resp = client.post("/api/import/school", json=_valid_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["counts"]["trinn"] == 2
    assert body["counts"]["classes"] == 3
    assert body["counts"]["class_groups"] == 5
    assert body["counts"]["teachers"] == 4
    assert body["counts"]["subjects"] == 4
    assert body["counts"]["activities"] == 3
    assert body["warnings"] == []
    school_year_id = body["school_year_id"]

    trinn = client.get("/api/trinn", params={"school_year_id": school_year_id}).json()
    assert len(trinn) == 2
    trinn_9 = next(t for t in trinn if t["level"] == 9)

    classes = client.get("/api/classes", params={"trinn_id": trinn_9["id"]}).json()
    class_9a = next(c for c in classes if c["name"] == "9A")
    groups = client.get("/api/class-groups", params={"school_class_id": class_9a["id"]}).json()
    assert {g["label"] for g in groups} == {"whole", "half1", "half2"}

    activities = client.get("/api/activities", params={"school_year_id": school_year_id}).json()
    assert len(activities) == 3
    trinnfag = next(a for a in activities if a["activity_type"] == "TRINNFAG")
    assert any(leg["class_group_id"] is None for leg in trinnfag["legs"])

    solve_resp = client.post("/api/solve", json={"school_year_id": school_year_id, "time_limit_seconds": 10})
    assert solve_resp.status_code == 200
    assert solve_resp.json()["status"] != "INFEASIBLE"


def test_import_reuses_existing_teacher_across_two_imports_same_zone(client):
    first = _valid_payload("2030/2031")
    resp1 = client.post("/api/import/school", json=first)
    assert resp1.status_code == 201

    teachers_after_first = client.get("/api/teachers").json()
    ab_id = next(t["id"] for t in teachers_after_first if t["initials"] == "AB")

    second = _valid_payload("2031/2032")
    second["teachers"] = [
        {"initials": "AB", "full_name": "Different Name"},
        {"initials": "CD", "full_name": "C D"},
        {"initials": "EF", "full_name": "E F"},
        {"initials": "GH", "full_name": "G H"},
    ]
    resp2 = client.post("/api/import/school", json=second)
    assert resp2.status_code == 201
    assert any("AB" in w["path"] or "AB" in w["message"] for w in resp2.json()["warnings"])

    teachers_after_second = client.get("/api/teachers").json()
    ab_rows = [t for t in teachers_after_second if t["initials"] == "AB"]
    assert len(ab_rows) == 1
    assert ab_rows[0]["id"] == ab_id
    assert ab_rows[0]["full_name"] == "A B"  # kept the original, not overwritten


def test_import_odd_duration_ticks_is_warning_not_error(client):
    payload = _valid_payload()
    payload["activities"][0]["duration_minutes"] = 90
    resp = client.post("/api/import/school", json=payload)
    assert resp.status_code == 201
    assert len(resp.json()["warnings"]) == 1


def test_import_requires_zone_header(client):
    payload = _valid_payload()
    resp = client.post("/api/import/school", json=payload, headers={"X-Zone-Id": ""})
    # An empty header value fails int() parsing in require_zone_header.
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "mutate,expected_message_fragment",
    [
        (lambda p: p["trinn"].append({"level": 8, "classes": []}), "Duplikate trinn"),
        (
            lambda p: p["activities"][0]["legs"].__setitem__(
                0, {"class_ref": "8A", "subject_code": "DOES_NOT_EXIST", "teacher_initials": ["AB"]}
            ),
            "Fagkode",
        ),
        (
            lambda p: p["activities"][0]["legs"].__setitem__(
                0, {"class_ref": "NOPE", "subject_code": "MA", "teacher_initials": ["AB"]}
            ),
            "Klasse",
        ),
        (
            lambda p: p["activities"][1]["legs"][0].__setitem__("class_ref", "9A:half9"),
            "Gruppe",
        ),
        (
            lambda p: p["activities"][0]["legs"][0].__setitem__("teacher_initials", ["ZZ"]),
            "Lærerinitialer",
        ),
        (
            lambda p: p["activities"].append(
                {
                    "activity_type": "NORMAL",
                    "duration_minutes": 60,
                    "occurrences_per_week": 1,
                    "legs": [
                        {"class_ref": "8A", "subject_code": "MA", "teacher_initials": []},
                        {"class_ref": "8A", "subject_code": "MA", "teacher_initials": []},
                    ],
                }
            ),
            "NORMAL",
        ),
        (lambda p: p["activities"][0].__setitem__("duration_minutes", 45), "duration_minutes"),
    ],
)
def test_import_validation_errors_are_all_or_nothing(client, mutate, expected_message_fragment):
    payload = copy.deepcopy(_valid_payload())
    mutate(payload)

    resp = client.post("/api/import/school", json=payload)
    assert resp.status_code == 422
    errors = resp.json()["detail"]["errors"]
    assert any(expected_message_fragment in e["message"] for e in errors)

    # Nothing was persisted -- no school year with this label exists.
    years = client.get(
        "/api/school-years",
    ).json()
    assert all(y["label"] != payload["school_year_label"] for y in years)


def test_import_duplicate_school_year_label_rejected(client):
    payload = _valid_payload()
    resp1 = client.post("/api/import/school", json=payload)
    assert resp1.status_code == 201

    resp2 = client.post("/api/import/school", json=_valid_payload())
    assert resp2.status_code == 422
    assert any("finnes allerede" in e["message"] for e in resp2.json()["detail"]["errors"])


def test_import_cannot_reuse_another_zones_teacher_by_initials(client):
    # Seed a second zone with a same-initials teacher directly via the DB,
    # bypassing the API (mirrors the existing IDOR test style).
    from app.db.models.teacher import Teacher

    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    other_zone = Zone(name="Other zone", created_at=datetime.now(timezone.utc).replace(tzinfo=None))
    db.add(other_zone)
    db.flush()
    other_teacher = Teacher(zone_id=other_zone.id, initials="AB", full_name="Someone Else")
    db.add(other_teacher)
    db.commit()
    other_teacher_id = other_teacher.id
    db.close()

    resp = client.post("/api/import/school", json=_valid_payload())
    assert resp.status_code == 201

    teachers = client.get("/api/teachers").json()
    ab_rows = [t for t in teachers if t["initials"] == "AB"]
    assert len(ab_rows) == 1
    assert ab_rows[0]["id"] != other_teacher_id
