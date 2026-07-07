from sqlalchemy import select

from app.db.models.period import DayOfWeek, PeriodDefinition
from app.solver.grid import build_tick_grid
from tests.fixtures.school_example_data import seed_school_example_data


def _grid(db_session):
    seed_school_example_data(db_session)
    periods = db_session.scalars(select(PeriodDefinition)).all()
    return build_tick_grid(periods)


def test_tick_counts_per_day(db_session):
    grid = _grid(db_session)

    for day in (DayOfWeek.MON, DayOfWeek.WED, DayOfWeek.THU, DayOfWeek.FRI):
        start, end = grid.day_range[day]
        assert end - start == 10  # 2+1+1+2+2+2

    tue_start, tue_end = grid.day_range[DayOfWeek.TUE]
    assert tue_end - tue_start == 6  # 2+1+1+2, short day

    assert grid.total_ticks == 10 * 4 + 6


def test_non_splittable_periods_move_together(db_session):
    grid = _grid(db_session)
    # Period 1 (non-splittable, 60 min) on Monday = ticks 0,1.
    assert (0, 1) in grid.non_splittable_pairs
    # A duration-1 (30 min) session can never start at tick 1 alone since
    # that would split period 1's pair -- but tick 1 is also not a valid
    # *start* for a 1-tick session anyway if it would leave the pair open;
    # more directly: a 1-tick session must not be placeable starting at
    # tick 0 or 1 of a non-splittable pair without covering both.
    starts_for_1_tick = set(grid.valid_start_ticks(1))
    assert 0 not in starts_for_1_tick
    assert 1 not in starts_for_1_tick


def test_period_2_and_3_are_independently_placeable(db_session):
    grid = _grid(db_session)
    p2 = grid.period2_tick[DayOfWeek.MON]
    p3 = grid.period3_tick[DayOfWeek.MON]
    assert p3 == p2 + 1
    starts_for_1_tick = set(grid.valid_start_ticks(1))
    assert p2 in starts_for_1_tick
    assert p3 in starts_for_1_tick


def test_sessions_cannot_span_lunch(db_session):
    grid = _grid(db_session)
    start, end = grid.day_range[DayOfWeek.MON]
    # Period 4 (before lunch) ends right before period 5 (after lunch);
    # a duration long enough to span from period 4 into period 5 must be
    # rejected as a valid start covering both sides.
    boundary = grid.lunch_boundary[DayOfWeek.MON]
    # 2-tick session starting at boundary-1 would straddle the lunch break.
    spanning_start = boundary - 1
    starts_for_2_ticks = set(grid.valid_start_ticks(2))
    assert spanning_start not in starts_for_2_ticks


def test_no_session_can_span_the_whole_day_across_lunch(db_session):
    grid = _grid(db_session)
    start, end = grid.day_range[DayOfWeek.MON]
    # A 10-tick (whole normal day) session would necessarily cross the
    # lunch boundary, so it must have no valid placement at all.
    starts = grid.valid_start_ticks(10)
    day_starts = [s for s in starts if start <= s < end]
    assert day_starts == []


def test_whole_pre_lunch_morning_fits_exactly_at_day_start(db_session):
    grid = _grid(db_session)
    start, end = grid.day_range[DayOfWeek.MON]
    # Periods 1-4 (2+1+1+2 = 6 ticks) are the entire pre-lunch block.
    starts = grid.valid_start_ticks(6)
    day_starts = [s for s in starts if start <= s < end]
    assert day_starts == [start]
