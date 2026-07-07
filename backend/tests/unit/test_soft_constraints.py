from datetime import time

from ortools.sat.python import cp_model

from app.db.models.period import DayOfWeek, PeriodDefinition
from app.solver.grid import build_tick_grid
from app.solver.model_builder import build_model
from app.solver.soft_constraints import add_soft_objective
from app.solver.types import LegData, SessionInstance, SolverSettingsData, SubjectData


def _grid(days=(DayOfWeek.MON,)):
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
                    school_year_id=1, day_of_week=day, period_number=number,
                    start_time=start, end_time=end,
                    is_splittable=splittable, is_before_lunch=before_lunch,
                )
            )
    return build_tick_grid(defs)


def _settings(**overrides):
    defaults = dict(
        max_concurrent_krov=2,
        preferred_concurrent_krov=1,
        krov10_preferred_periods=(3, 4),
        weight_musikk_spread=10,
        weight_matte_before_lunch=10,
        weight_mat_helse_placement=10,
        weight_krov_prefer_one=5,
    )
    defaults.update(overrides)
    return SolverSettingsData(**defaults)


def _subject(id_, **kwargs):
    defaults = dict(
        short_code=f"S{id_}", is_krov=False, uses_hall=False, is_trinnfag=False,
        avoid_consecutive=False, prefer_before_lunch=False, needs_consecutive_periods=False,
    )
    defaults.update(kwargs)
    return SubjectData(id=id_, **defaults)


def _optimize(grid, sessions, subjects_by_id, settings, krov10_keys=None):
    built = build_model(grid, sessions, subjects_by_id, [])
    add_soft_objective(built.model, built, grid, sessions, subjects_by_id, settings, krov10_keys)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    status = solver.Solve(built.model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    def assigned(key):
        for s, var in built.start_vars[key].items():
            if solver.Value(var):
                return s
        raise AssertionError("no start assigned")

    return solver, assigned


def test_matte_prefers_before_lunch_when_both_are_free():
    grid = _grid()
    matte = _subject(1, prefer_before_lunch=True)
    sessions = [
        SessionInstance(key="matte", activity_id=1, occurrence_index=0, duration_ticks=2,
                         legs=(LegData(class_group_id=100, subject_id=1, teacher_ids=(1,)),)),
    ]
    _, assigned = _optimize(grid, sessions, {1: matte}, _settings())
    day_start, _ = grid.day_range[DayOfWeek.MON]
    lunch = grid.lunch_boundary[DayOfWeek.MON]
    assert assigned("matte") < lunch


def test_mat_helse_prefers_starting_at_period_2():
    grid = _grid()
    mh = _subject(1, short_code="MH", needs_consecutive_periods=True)
    sessions = [
        SessionInstance(key="mh", activity_id=1, occurrence_index=0, duration_ticks=2,
                         legs=(LegData(class_group_id=100, subject_id=1, teacher_ids=(1,)),)),
    ]
    _, assigned = _optimize(grid, sessions, {1: mh}, _settings())
    start = assigned("mh")
    assert grid.ticks[start].period_number == 2


def test_musikk_avoids_two_consecutive_periods_for_same_class():
    grid = _grid()
    musikk = _subject(1, avoid_consecutive=True)
    # Two 30-min Musikk sessions for the same class, both must be placed
    # somewhere -- with periods 2/3 already taken by adjacency pairing
    # rules they'll need placement among the splittable ticks or as a
    # merged 60-min block; force via two separate NORMAL 60-min sessions
    # on periods that could be adjacent (P1+P4 vs the non-adjacent P1+P6)
    # by giving the solver two occurrences with free placement.
    sessions = [
        SessionInstance(key="mus1", activity_id=1, occurrence_index=0, duration_ticks=2,
                         legs=(LegData(class_group_id=100, subject_id=1, teacher_ids=(1,)),)),
        SessionInstance(key="mus2", activity_id=1, occurrence_index=1, duration_ticks=2,
                         legs=(LegData(class_group_id=100, subject_id=1, teacher_ids=(1,)),)),
    ]
    _, assigned = _optimize(grid, sessions, {1: musikk}, _settings())
    p1 = grid.ticks[assigned("mus1")].period_number
    p2 = grid.ticks[assigned("mus2")].period_number
    assert abs(p1 - p2) != 1


def test_krov_prefers_only_one_concurrent_session():
    grid = _grid()
    krov = _subject(1, is_krov=True)
    # Two KRØV sessions for different classes -- hard cap allows 2
    # concurrent, but the soft objective should push the solver to spread
    # them across different ticks instead when it's free to do so.
    sessions = [
        SessionInstance(key="k1", activity_id=1, occurrence_index=0, duration_ticks=2,
                         legs=(LegData(class_group_id=100, subject_id=1, teacher_ids=(1,)),)),
        SessionInstance(key="k2", activity_id=2, occurrence_index=0, duration_ticks=2,
                         legs=(LegData(class_group_id=101, subject_id=1, teacher_ids=(2,)),)),
    ]
    _, assigned = _optimize(grid, sessions, {1: krov}, _settings())
    assert assigned("k1") != assigned("k2")
