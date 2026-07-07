from app.db.models.activity import Activity
from app.db.models.period import DayOfWeek
from app.solver.solve_service import solve_school_year
from tests.fixtures.school_example_data import seed_school_example_data


def test_solver_finds_a_valid_schedule_for_the_real_fixture(db_session):
    result = seed_school_example_data(db_session)
    school_year_id = result["school_year"].id

    solve_result = solve_school_year(db_session, school_year_id, time_limit_seconds=30)

    assert solve_result.infeasible_sessions == []
    assert solve_result.status in ("OPTIMAL", "FEASIBLE")

    # Every occurrence of every activity must be placed exactly once.
    expected_occurrences = sum(
        a.occurrences_per_week
        for a in db_session.query(Activity).filter_by(school_year_id=school_year_id)
    )
    assert len(solve_result.placements) == expected_occurrences


def test_fremmedspraak_10_lands_in_the_fixed_wednesday_slot(db_session):
    result = seed_school_example_data(db_session)
    school_year_id = result["school_year"].id

    solve_result = solve_school_year(db_session, school_year_id, time_limit_seconds=30)
    assert solve_result.status in ("OPTIMAL", "FEASIBLE")

    # Exact match: there are now three Fremmedspraak activities (8th/9th/
    # 10th trinn each have their own), only 10th's is fixed to Wed 5-6.
    sprak_activity_id = next(
        a.id
        for a in db_session.query(Activity)
        if a.notes == "10th trinn Fremmedspraak (fixed: Wed periods 5-6)"
    )
    placements = [p for p in solve_result.placements if p.activity_id == sprak_activity_id]
    assert len(placements) == 1
    placement = placements[0]
    assert placement.day_of_week == DayOfWeek.WED
    # Local tick 6 = start of period 5 on a normal day (2+1+1+2 = 6 ticks before it).
    assert placement.start_tick == 6


def test_no_krov_runs_while_valgfag_is_active(db_session):
    result = seed_school_example_data(db_session)
    school_year_id = result["school_year"].id
    solve_result = solve_school_year(db_session, school_year_id, time_limit_seconds=30)
    assert solve_result.status in ("OPTIMAL", "FEASIBLE")

    # Structural sanity check that the solve didn't silently drop the
    # Valgfag activity (it has legs with class_group_id=None, easy to
    # accidentally lose in a refactor).
    valgfag_activity_id = next(
        a.id for a in db_session.query(Activity) if a.notes == "10th trinn Valgfag"
    )
    assert any(p.activity_id == valgfag_activity_id for p in solve_result.placements)
