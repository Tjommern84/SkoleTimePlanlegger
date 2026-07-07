from sqlalchemy import select

from app.db.models.activity import Activity, ActivityLeg
from app.db.models.subject import SubjectHourAllocation
from app.db.models.trinn_class import ClassGroup
from tests.fixtures.school_example_data import seed_school_example_data


def test_seed_creates_full_hour_table_and_classes(db_session):
    result = seed_school_example_data(db_session)

    assert len(result["classes"]) == 9
    assert set(result["classes"]) == {
        "8A", "8B", "8C", "9A", "9B", "9C", "10A", "10B", "10C",
    }

    # 9A has whole + half1 + half2; every other class has only "whole".
    class_groups = db_session.scalars(select(ClassGroup)).all()
    assert len(class_groups) == 9 + 2

    allocations = db_session.scalars(select(SubjectHourAllocation)).all()
    per_trinn_sum: dict[int, float] = {}
    for alloc in allocations:
        per_trinn_sum[alloc.trinn_id] = per_trinn_sum.get(alloc.trinn_id, 0) + float(alloc.weekly_hours)
    assert list(per_trinn_sum.values()) == [23.0, 23.0, 23.0]


def test_seed_covers_three_tricky_patterns(db_session):
    result = seed_school_example_data(db_session)

    activities = db_session.scalars(select(Activity)).all()
    notes = {a.notes for a in activities}

    assert "8A Norsk co-taught" in notes
    assert "8B Norsk co-taught" in notes
    assert "8C Norsk co-taught" in notes
    assert "9A Mat&Helse / Naturfag split" in notes
    assert "10th trinn Valgfag" in notes
    assert "10th trinn Fremmedspraak (fixed: Wed periods 5-6)" in notes

    split_activity = next(a for a in activities if a.notes == "9A Mat&Helse / Naturfag split")
    legs = db_session.scalars(
        select(ActivityLeg).where(ActivityLeg.activity_id == split_activity.id)
    ).all()
    assert len(legs) == 2
    assert {leg.class_group_id for leg in legs} == {
        result["class_groups"]["9A-half1"].id,
        result["class_groups"]["9A-half2"].id,
    }
    # The two legs must carry different subjects (Mat&Helse vs Naturfag).
    assert len({leg.subject_id for leg in legs}) == 2

    valgfag_activity = next(a for a in activities if a.notes == "10th trinn Valgfag")
    valgfag_legs = db_session.scalars(
        select(ActivityLeg).where(ActivityLeg.activity_id == valgfag_activity.id)
    ).all()
    assert len(valgfag_legs) == 4
    # The 4th parallel teacher group has no home class of its own.
    assert sum(1 for leg in valgfag_legs if leg.class_group_id is None) == 1
