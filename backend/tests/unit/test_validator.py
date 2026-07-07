from ortools.sat.python import cp_model

from app.solver.model_builder import build_model
from app.solver.solve_service import load_solve_inputs
from app.solver.validator import validate
from tests.fixtures.school_example_data import seed_school_example_data


def _solve_and_get_placements(inputs):
    built = build_model(
        inputs.grid,
        inputs.sessions,
        inputs.subjects_by_id,
        inputs.teacher_unavailabilities,
        mutually_exclusive_group_pairs=inputs.mutually_exclusive_pairs,
        max_concurrent_krov=inputs.max_concurrent_krov,
    )
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30
    status = solver.Solve(built.model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    placements = {}
    for key, tick_vars in built.start_vars.items():
        for tick, var in tick_vars.items():
            if solver.Value(var):
                placements[key] = tick
                break
    return placements


def test_validator_reports_zero_violations_for_a_real_solve(db_session):
    result = seed_school_example_data(db_session)
    inputs = load_solve_inputs(db_session, result["school_year"].id)
    placements = _solve_and_get_placements(inputs)

    violations = validate(
        inputs.grid,
        inputs.sessions,
        placements,
        inputs.subjects_by_id,
        inputs.teacher_unavailabilities,
        mutually_exclusive_group_pairs=inputs.mutually_exclusive_pairs,
        max_concurrent_krov=inputs.max_concurrent_krov,
    )
    assert violations == []


def test_validator_catches_a_deliberately_double_booked_teacher(db_session):
    result = seed_school_example_data(db_session)
    inputs = load_solve_inputs(db_session, result["school_year"].id)
    placements = _solve_and_get_placements(inputs)

    # Corrupt the solution: force two sessions that share a teacher onto
    # the exact same tick (8A Norsk co-taught and 8B Norsk co-taught share
    # teacher GB).
    sessions_by_key = {s.key: s for s in inputs.sessions}
    gb_sessions = [
        key
        for key, s in sessions_by_key.items()
        if any(1 in leg.teacher_ids or 3 in leg.teacher_ids for leg in s.legs)
    ]
    assert len(gb_sessions) >= 2
    placements[gb_sessions[1]] = placements[gb_sessions[0]]

    violations = validate(
        inputs.grid,
        inputs.sessions,
        placements,
        inputs.subjects_by_id,
        inputs.teacher_unavailabilities,
        mutually_exclusive_group_pairs=inputs.mutually_exclusive_pairs,
        max_concurrent_krov=inputs.max_concurrent_krov,
    )
    kinds = {v.kind for v in violations}
    assert "teacher_double_booked" in kinds


def test_validator_catches_a_stranded_half_hour(db_session):
    result = seed_school_example_data(db_session)
    inputs = load_solve_inputs(db_session, result["school_year"].id)
    placements = _solve_and_get_placements(inputs)

    p2 = inputs.grid.period2_tick[list(inputs.grid.period2_tick)[0]]
    # Pick any placed session and force it into a lone half-hour tick with
    # duration shrunk conceptually by re-pointing it at p2 only (this is a
    # deliberately invalid placement, not a duration change -- validator
    # should flag it as an invalid placement AND/OR a stranded half-hour).
    any_key = next(iter(placements))
    placements[any_key] = p2

    violations = validate(
        inputs.grid,
        inputs.sessions,
        placements,
        inputs.subjects_by_id,
        inputs.teacher_unavailabilities,
        mutually_exclusive_group_pairs=inputs.mutually_exclusive_pairs,
        max_concurrent_krov=inputs.max_concurrent_krov,
    )
    assert len(violations) > 0
