from app.solver.expand import expand_activities
from app.solver.types import ActivityData, LegData


def test_expand_creates_one_instance_per_occurrence():
    activity = ActivityData(
        id=1,
        activity_type="NORMAL",
        duration_ticks=2,
        occurrences_per_week=3,
        legs=(LegData(class_group_id=10, subject_id=1, teacher_ids=(5, 6)),),
    )
    instances = expand_activities([activity])
    assert len(instances) == 3
    assert {i.occurrence_index for i in instances} == {0, 1, 2}
    assert all(i.duration_ticks == 2 for i in instances)
    assert all(i.legs == activity.legs for i in instances)
    assert len({i.key for i in instances}) == 3  # unique keys


def test_expand_applies_fixed_placement_to_all_occurrences_of_that_activity():
    activity = ActivityData(
        id=2,
        activity_type="TRINNFAG",
        duration_ticks=4,
        occurrences_per_week=1,
        legs=(LegData(class_group_id=None, subject_id=9, teacher_ids=(1,)),),
    )
    other = ActivityData(
        id=3,
        activity_type="NORMAL",
        duration_ticks=2,
        occurrences_per_week=1,
        legs=(LegData(class_group_id=10, subject_id=1, teacher_ids=(2,)),),
    )
    instances = expand_activities([activity, other], fixed_placements={2: 36})
    fixed = [i for i in instances if i.activity_id == 2]
    unfixed = [i for i in instances if i.activity_id == 3]
    assert fixed[0].fixed_start_tick == 36
    assert unfixed[0].fixed_start_tick is None
