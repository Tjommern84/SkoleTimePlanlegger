from datetime import time

from ortools.sat.python import cp_model

from app.db.models.period import DayOfWeek, PeriodDefinition
from app.solver.grid import build_tick_grid
from app.solver.model_builder import build_model
from app.solver.types import LegData, SessionInstance, SubjectData, TeacherUnavailabilityData


def _normal_day_grid(days=(DayOfWeek.MON,)):
    defs = []
    layout = [
        (1, time(8, 30), time(9, 30), False, True),
        (2, time(9, 30), time(10, 0), True, True),
        (3, time(10, 10), time(10, 40), True, True),
        (4, time(10, 40), time(11, 40), False, True),
        (5, time(12, 20), time(13, 20), False, False),
        (6, time(13, 30), time(14, 30), False, False),
    ]
    for day in days:
        for number, start, end, splittable, before_lunch in layout:
            defs.append(
                PeriodDefinition(
                    school_year_id=1,
                    day_of_week=day,
                    period_number=number,
                    start_time=start,
                    end_time=end,
                    is_splittable=splittable,
                    is_before_lunch=before_lunch,
                )
            )
    return build_tick_grid(defs)


def _subject(id_, **kwargs):
    defaults = dict(
        short_code=f"S{id_}",
        is_krov=False,
        uses_hall=False,
        is_trinnfag=False,
        avoid_consecutive=False,
        prefer_before_lunch=False,
        needs_consecutive_periods=False,
    )
    defaults.update(kwargs)
    return SubjectData(id=id_, **defaults)


def _solve(built):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    status = solver.Solve(built.model)
    return solver, status


def test_two_sessions_same_teacher_forced_to_different_ticks():
    grid = _normal_day_grid()
    subj = _subject(1)
    # Both are 60-min (2-tick) sessions -- avoids the half-hour adjacency
    # rule entirely (they either occupy a whole non-splittable period, or
    # both P2+P3 ticks together) so this isolates the teacher no-overlap
    # constraint: same teacher on both, must land on different ticks.
    sessions = [
        SessionInstance(key="a", activity_id=1, occurrence_index=0, duration_ticks=2,
                         legs=(LegData(class_group_id=100, subject_id=1, teacher_ids=(1,)),)),
        SessionInstance(key="b", activity_id=2, occurrence_index=0, duration_ticks=2,
                         legs=(LegData(class_group_id=101, subject_id=1, teacher_ids=(1,)),)),
    ]
    built = build_model(grid, sessions, {1: subj}, [])
    solver, status = _solve(built)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    def assigned_tick(key):
        for s, var in built.start_vars[key].items():
            if solver.Value(var):
                return s
        raise AssertionError("no start assigned")

    assert assigned_tick("a") != assigned_tick("b")


def test_teacher_double_booking_is_infeasible_when_forced():
    grid = _normal_day_grid()
    subj = _subject(1)
    p2 = grid.period2_tick[DayOfWeek.MON]
    # Force both sessions to the exact same single valid tick by fixing it.
    sessions = [
        SessionInstance(key="a", activity_id=1, occurrence_index=0, duration_ticks=1,
                         legs=(LegData(class_group_id=100, subject_id=1, teacher_ids=(1,)),),
                         fixed_start_tick=p2),
        SessionInstance(key="b", activity_id=2, occurrence_index=0, duration_ticks=1,
                         legs=(LegData(class_group_id=101, subject_id=1, teacher_ids=(1,)),),
                         fixed_start_tick=p2),
    ]
    built = build_model(grid, sessions, {1: subj}, [])
    _, status = _solve(built)
    assert status == cp_model.INFEASIBLE


def test_krov_cap_allows_two_but_not_three():
    grid = _normal_day_grid()
    subj = _subject(1, is_krov=True)
    p1 = grid.day_range[DayOfWeek.MON][0]
    sessions = [
        SessionInstance(key=f"k{i}", activity_id=i, occurrence_index=0, duration_ticks=2,
                         legs=(LegData(class_group_id=100 + i, subject_id=1, teacher_ids=(i,)),),
                         fixed_start_tick=p1)
        for i in range(3)
    ]
    built = build_model(grid, sessions, {1: subj}, [])
    _, status = _solve(built)
    assert status == cp_model.INFEASIBLE

    built2 = build_model(grid, sessions[:2], {1: subj}, [])
    _, status2 = _solve(built2)
    assert status2 in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_hall_use_blocks_all_krov_school_wide():
    grid = _normal_day_grid()
    krov_subj = _subject(1, is_krov=True)
    hall_subj = _subject(2, uses_hall=True)
    p1 = grid.day_range[DayOfWeek.MON][0]
    sessions = [
        SessionInstance(key="krov", activity_id=1, occurrence_index=0, duration_ticks=2,
                         legs=(LegData(class_group_id=100, subject_id=1, teacher_ids=(1,)),),
                         fixed_start_tick=p1),
        SessionInstance(key="valgfag", activity_id=2, occurrence_index=0, duration_ticks=2,
                         legs=(LegData(class_group_id=200, subject_id=2, teacher_ids=(2,)),),
                         fixed_start_tick=p1),
    ]
    built = build_model(grid, sessions, {1: krov_subj, 2: hall_subj}, [])
    _, status = _solve(built)
    assert status == cp_model.INFEASIBLE  # KRØV cannot run while the hall is in use


def test_fremmedspraak_not_hall_does_not_block_krov():
    grid = _normal_day_grid()
    krov_subj = _subject(1, is_krov=True)
    sprak_subj = _subject(2, is_trinnfag=True, uses_hall=False)
    p1 = grid.day_range[DayOfWeek.MON][0]
    sessions = [
        SessionInstance(key="krov", activity_id=1, occurrence_index=0, duration_ticks=2,
                         legs=(LegData(class_group_id=100, subject_id=1, teacher_ids=(1,)),),
                         fixed_start_tick=p1),
        SessionInstance(key="sprak", activity_id=2, occurrence_index=0, duration_ticks=2,
                         legs=(LegData(class_group_id=200, subject_id=2, teacher_ids=(2,)),),
                         fixed_start_tick=p1),
    ]
    built = build_model(grid, sessions, {1: krov_subj, 2: sprak_subj}, [])
    _, status = _solve(built)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_half_hour_stranding_is_rejected():
    grid = _normal_day_grid()
    subj = _subject(1)
    p2 = grid.period2_tick[DayOfWeek.MON]
    # A single 30-min session pinned to period 2 only, nothing else placed
    # for that class-group at period 3 -- must be infeasible.
    sessions = [
        SessionInstance(key="lone", activity_id=1, occurrence_index=0, duration_ticks=1,
                         legs=(LegData(class_group_id=100, subject_id=1, teacher_ids=(1,)),),
                         fixed_start_tick=p2),
    ]
    built = build_model(grid, sessions, {1: subj}, [])
    _, status = _solve(built)
    assert status == cp_model.INFEASIBLE


def test_paired_half_hours_are_accepted():
    grid = _normal_day_grid()
    subj = _subject(1)
    p2 = grid.period2_tick[DayOfWeek.MON]
    p3 = grid.period3_tick[DayOfWeek.MON]
    sessions = [
        SessionInstance(key="first", activity_id=1, occurrence_index=0, duration_ticks=1,
                         legs=(LegData(class_group_id=100, subject_id=1, teacher_ids=(1,)),),
                         fixed_start_tick=p2),
        SessionInstance(key="second", activity_id=2, occurrence_index=0, duration_ticks=1,
                         legs=(LegData(class_group_id=100, subject_id=1, teacher_ids=(2,)),),
                         fixed_start_tick=p3),
    ]
    built = build_model(grid, sessions, {1: subj}, [])
    _, status = _solve(built)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_whole_and_half_group_are_mutually_exclusive():
    grid = _normal_day_grid()
    subj = _subject(1)
    p1 = grid.day_range[DayOfWeek.MON][0]
    whole_id, half_id = 100, 101
    sessions = [
        SessionInstance(key="whole", activity_id=1, occurrence_index=0, duration_ticks=2,
                         legs=(LegData(class_group_id=whole_id, subject_id=1, teacher_ids=(1,)),),
                         fixed_start_tick=p1),
        SessionInstance(key="half", activity_id=2, occurrence_index=0, duration_ticks=2,
                         legs=(LegData(class_group_id=half_id, subject_id=1, teacher_ids=(2,)),),
                         fixed_start_tick=p1),
    ]
    built = build_model(
        grid, sessions, {1: subj}, [], mutually_exclusive_group_pairs=[(whole_id, half_id)]
    )
    _, status = _solve(built)
    assert status == cp_model.INFEASIBLE


def test_teacher_unavailability_blocks_the_forbidden_tick():
    grid = _normal_day_grid()
    subj = _subject(1)
    p1 = grid.day_range[DayOfWeek.MON][0]
    sessions = [
        SessionInstance(key="a", activity_id=1, occurrence_index=0, duration_ticks=2,
                         legs=(LegData(class_group_id=100, subject_id=1, teacher_ids=(1,)),),
                         fixed_start_tick=p1),
    ]
    unavail = [TeacherUnavailabilityData(teacher_id=1, day_of_week=DayOfWeek.MON, start_period=None, end_period=None)]
    built = build_model(grid, sessions, {1: subj}, unavail)
    _, status = _solve(built)
    assert status == cp_model.INFEASIBLE
