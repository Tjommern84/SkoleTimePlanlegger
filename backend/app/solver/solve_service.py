"""Orchestrates a full solve for one school year: load domain data from the
DB, build the tick grid + CP-SAT model, solve, and translate the result
back into plain placements. Phase 2 scope: hard constraints only, no
persistence yet (see docs/domain-notes.md Phase 4 for that).
"""

from dataclasses import dataclass

from ortools.sat.python import cp_model
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models.activity import Activity, ActivityLeg
from app.db.models.period import DayOfWeek, PeriodDefinition
from app.db.models.solver_settings import SolverSettings
from app.db.models.subject import Subject
from app.db.models.teacher import TeacherUnavailability
from app.db.models.trinn_class import ClassGroup, SchoolClass, Trinn
from app.solver.expand import expand_activities
from app.solver.grid import TickGrid, build_tick_grid
from app.solver.model_builder import BuiltModel, build_model
from app.solver.soft_constraints import add_soft_objective
from app.solver.types import (
    ActivityData,
    LegData,
    SessionInstance,
    SolverSettingsData,
    SubjectData,
    TeacherUnavailabilityData,
)


@dataclass
class Placement:
    activity_id: int
    occurrence_index: int
    day_of_week: DayOfWeek
    start_tick: int  # 0-based, local to the day
    duration_ticks: int


@dataclass
class SolveResult:
    status: str  # "OPTIMAL" / "FEASIBLE" / "INFEASIBLE" / "UNKNOWN"
    placements: list[Placement]
    infeasible_sessions: list[str]


def _load_grid(db: Session, school_year_id: int) -> TickGrid:
    periods = db.scalars(
        select(PeriodDefinition).where(PeriodDefinition.school_year_id == school_year_id)
    ).all()
    return build_tick_grid(list(periods))


def _load_activities(db: Session, school_year_id: int) -> list[ActivityData]:
    stmt = (
        select(Activity)
        .where(Activity.school_year_id == school_year_id)
        .options(selectinload(Activity.legs).selectinload(ActivityLeg.leg_teachers))
    )
    activities = db.scalars(stmt).all()
    return [
        ActivityData(
            id=a.id,
            activity_type=a.activity_type.value,
            duration_ticks=a.duration_ticks,
            occurrences_per_week=a.occurrences_per_week,
            legs=tuple(
                LegData(
                    class_group_id=leg.class_group_id,
                    subject_id=leg.subject_id,
                    teacher_ids=tuple(lt.teacher_id for lt in leg.leg_teachers),
                )
                for leg in a.legs
            ),
        )
        for a in activities
    ]


def _load_subjects(db: Session, school_year_id: int) -> dict[int, SubjectData]:
    subjects = db.scalars(select(Subject).where(Subject.school_year_id == school_year_id)).all()
    return {
        s.id: SubjectData(
            id=s.id,
            short_code=s.short_code,
            is_krov=s.is_krov,
            uses_hall=s.uses_hall,
            is_trinnfag=s.is_trinnfag,
            avoid_consecutive=s.avoid_consecutive,
            prefer_before_lunch=s.prefer_before_lunch,
            needs_consecutive_periods=s.needs_consecutive_periods,
            prefer_early_periods=s.prefer_early_periods,
            avoid_friday_afternoon=s.avoid_friday_afternoon,
        )
        for s in subjects
    }


def _load_teacher_unavailabilities(db: Session, school_year_id: int) -> list[TeacherUnavailabilityData]:
    rows = db.scalars(
        select(TeacherUnavailability).where(TeacherUnavailability.school_year_id == school_year_id)
    ).all()
    return [
        TeacherUnavailabilityData(
            teacher_id=r.teacher_id,
            day_of_week=r.day_of_week,
            start_period=r.start_period,
            end_period=r.end_period,
        )
        for r in rows
    ]


def _load_mutually_exclusive_group_pairs(db: Session, school_year_id: int) -> list[tuple[int, int]]:
    """(whole_group_id, half_group_id) pairs within the same school class --
    they represent the same students and must never both be active.
    """
    stmt = (
        select(ClassGroup)
        .join(SchoolClass, ClassGroup.school_class_id == SchoolClass.id)
        .join(Trinn, SchoolClass.trinn_id == Trinn.id)
        .where(Trinn.school_year_id == school_year_id)
    )
    groups = db.scalars(stmt).all()
    by_class: dict[int, list[ClassGroup]] = {}
    for g in groups:
        by_class.setdefault(g.school_class_id, []).append(g)

    pairs: list[tuple[int, int]] = []
    for class_groups in by_class.values():
        whole = next((g for g in class_groups if g.label == "whole"), None)
        if whole is None:
            continue
        for g in class_groups:
            if g.id != whole.id:
                pairs.append((whole.id, g.id))
    return pairs


def _class_group_trinn_level(db: Session, school_year_id: int) -> dict[int, int]:
    stmt = (
        select(ClassGroup, Trinn.level)
        .join(SchoolClass, ClassGroup.school_class_id == SchoolClass.id)
        .join(Trinn, SchoolClass.trinn_id == Trinn.id)
        .where(Trinn.school_year_id == school_year_id)
    )
    return {group.id: level for group, level in db.execute(stmt).all()}


def _resolve_fixed_placements(
    db: Session, school_year_id: int, grid: TickGrid, activities: list[ActivityData]
) -> dict[int, int]:
    """10th-trinn Fremmedspraak must land in a fixed (day, period) slot per
    SolverSettings -- identified as a trinnfag, non-hall-using activity
    whose legs belong to trinn-10 classes.
    """
    settings = db.scalars(
        select(SolverSettings).where(SolverSettings.school_year_id == school_year_id)
    ).first()
    if settings is None:
        return {}

    fixed_day = DayOfWeek(settings.fremmedspraak10_fixed_day)
    fixed_start_period = int(settings.fremmedspraak10_fixed_periods.split(",")[0])
    fixed_tick = grid.fixed_start_tick(fixed_day, fixed_start_period)
    if fixed_tick is None:
        return {}

    subject_rows = {
        s.id: s
        for s in db.scalars(select(Subject).where(Subject.school_year_id == school_year_id)).all()
    }
    class_group_trinn_level = _class_group_trinn_level(db, school_year_id)

    fixed_placements: dict[int, int] = {}
    for activity in activities:
        if activity.activity_type != "TRINNFAG":
            continue
        is_sprak_10 = False
        for leg in activity.legs:
            subject = subject_rows.get(leg.subject_id)
            if subject is None or not subject.is_trinnfag or subject.uses_hall:
                continue
            if leg.class_group_id is not None and class_group_trinn_level.get(leg.class_group_id) == 10:
                is_sprak_10 = True
        if is_sprak_10:
            fixed_placements[activity.id] = fixed_tick
    return fixed_placements


def _resolve_krov10_session_keys(
    db: Session, school_year_id: int, sessions: list[SessionInstance]
) -> set[str]:
    """Session keys for KROV activities whose legs belong to trinn-10
    classes -- these get the krov10_preferred_periods soft placement
    preference (Phase 3).
    """
    subject_rows = {
        s.id: s
        for s in db.scalars(select(Subject).where(Subject.school_year_id == school_year_id)).all()
    }
    class_group_trinn_level = _class_group_trinn_level(db, school_year_id)

    keys: set[str] = set()
    for session in sessions:
        for leg in session.legs:
            subject = subject_rows.get(leg.subject_id)
            if (
                subject is not None
                and subject.is_krov
                and leg.class_group_id is not None
                and class_group_trinn_level.get(leg.class_group_id) == 10
            ):
                keys.add(session.key)
    return keys


def _load_solver_settings_data(db: Session, school_year_id: int) -> SolverSettingsData:
    settings = db.scalars(
        select(SolverSettings).where(SolverSettings.school_year_id == school_year_id)
    ).first()
    if settings is None:
        return SolverSettingsData(
            max_concurrent_krov=2,
            preferred_concurrent_krov=1,
            krov10_preferred_periods=(3, 4),
            weight_musikk_spread=10,
            weight_matte_before_lunch=10,
            weight_mat_helse_placement=10,
            weight_krov_prefer_one=5,
            weight_prefer_early_periods=10,
            weight_avoid_friday_afternoon=10,
        )
    return SolverSettingsData(
        max_concurrent_krov=settings.max_concurrent_krov,
        preferred_concurrent_krov=settings.preferred_concurrent_krov,
        krov10_preferred_periods=tuple(
            int(p) for p in settings.krov10_preferred_periods.split(",") if p.strip()
        ),
        weight_musikk_spread=settings.weight_musikk_spread,
        weight_matte_before_lunch=settings.weight_matte_before_lunch,
        weight_mat_helse_placement=settings.weight_mat_helse_placement,
        weight_krov_prefer_one=settings.weight_krov_prefer_one,
        weight_prefer_early_periods=settings.weight_prefer_early_periods,
        weight_avoid_friday_afternoon=settings.weight_avoid_friday_afternoon,
    )


@dataclass
class SolveInputs:
    grid: TickGrid
    sessions: list[SessionInstance]
    subjects_by_id: dict[int, SubjectData]
    teacher_unavailabilities: list[TeacherUnavailabilityData]
    mutually_exclusive_pairs: list[tuple[int, int]]
    max_concurrent_krov: int
    settings_data: SolverSettingsData
    krov10_session_keys: set[str]


def load_solve_inputs(db: Session, school_year_id: int) -> SolveInputs:
    """Loads and expands everything build_model/validate need. Shared by
    solve_school_year and by tests that want to run the independent
    validator against a solve's output.
    """
    grid = _load_grid(db, school_year_id)
    activities = _load_activities(db, school_year_id)
    subjects_by_id = _load_subjects(db, school_year_id)
    teacher_unavailabilities = _load_teacher_unavailabilities(db, school_year_id)
    mutually_exclusive_pairs = _load_mutually_exclusive_group_pairs(db, school_year_id)
    fixed_placements = _resolve_fixed_placements(db, school_year_id, grid, activities)
    settings_data = _load_solver_settings_data(db, school_year_id)

    sessions = expand_activities(activities, fixed_placements)
    krov10_session_keys = _resolve_krov10_session_keys(db, school_year_id, sessions)

    return SolveInputs(
        grid=grid,
        sessions=sessions,
        subjects_by_id=subjects_by_id,
        teacher_unavailabilities=teacher_unavailabilities,
        mutually_exclusive_pairs=mutually_exclusive_pairs,
        max_concurrent_krov=settings_data.max_concurrent_krov,
        settings_data=settings_data,
        krov10_session_keys=krov10_session_keys,
    )


_STATUS_NAMES = {
    cp_model.OPTIMAL: "OPTIMAL",
    cp_model.FEASIBLE: "FEASIBLE",
    cp_model.INFEASIBLE: "INFEASIBLE",
}


def _extract_placements(built: BuiltModel, solver: cp_model.CpSolver, grid: TickGrid, sessions: list[SessionInstance]) -> list[Placement]:
    session_by_key = {s.key: s for s in sessions}
    placements: list[Placement] = []
    for key, tick_vars in built.start_vars.items():
        session = session_by_key[key]
        for tick, var in tick_vars.items():
            if solver.Value(var):
                day, local_tick = grid.day_and_local_tick(tick)
                placements.append(
                    Placement(
                        activity_id=session.activity_id,
                        occurrence_index=session.occurrence_index,
                        day_of_week=day,
                        start_tick=local_tick,
                        duration_ticks=session.duration_ticks,
                    )
                )
                break
    return placements


def solve_school_year(
    db: Session, school_year_id: int, time_limit_seconds: float = 60.0, optimize: bool = True
) -> SolveResult:
    return solve_school_year_variants(
        db, school_year_id, time_limit_seconds=time_limit_seconds, optimize=optimize, variant_count=1
    )[0]


def solve_school_year_variants(
    db: Session,
    school_year_id: int,
    time_limit_seconds: float = 60.0,
    optimize: bool = True,
    variant_count: int = 1,
) -> list[SolveResult]:
    """Returns up to variant_count distinct, equally-valid solve results.

    CP-SAT's default search is deterministic and -- for problems small
    enough to hit a proven-optimal (often zero-penalty) solution almost
    immediately -- re-running with a different random_seed alone does NOT
    surface a different solution, since the search stops as soon as
    optimality is proven. Randomizing search order doesn't help either
    (verified empirically). The only reliable way to get a genuinely
    different equally-good solution is to explicitly forbid the exact
    assignment just found (a "no-good" cut: at least one of its true
    boolean variables must become false) and re-solve the same model.
    Subsequent variants are not ranked or guaranteed better/worse than the
    first -- they're alternates with the same objective value (or worse,
    if the search space of equally-optimal solutions is exhausted).
    """
    inputs = load_solve_inputs(db, school_year_id)
    grid = inputs.grid
    sessions = inputs.sessions

    built = build_model(
        grid,
        sessions,
        inputs.subjects_by_id,
        inputs.teacher_unavailabilities,
        mutually_exclusive_group_pairs=inputs.mutually_exclusive_pairs,
        max_concurrent_krov=inputs.max_concurrent_krov,
    )

    if built.infeasible_sessions:
        return [SolveResult(status="INFEASIBLE", placements=[], infeasible_sessions=built.infeasible_sessions)]

    if optimize:
        add_soft_objective(
            built.model,
            built,
            grid,
            sessions,
            inputs.subjects_by_id,
            inputs.settings_data,
            krov10_session_keys=inputs.krov10_session_keys,
        )

    all_vars = [var for tick_vars in built.start_vars.values() for var in tick_vars.values()]

    results: list[SolveResult] = []
    for i in range(max(variant_count, 1)):
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_seconds
        solver.parameters.num_search_workers = 8
        status_code = solver.Solve(built.model)
        status = _STATUS_NAMES.get(status_code, "UNKNOWN")

        if status not in ("OPTIMAL", "FEASIBLE"):
            if i == 0:
                results.append(SolveResult(status=status, placements=[], infeasible_sessions=[]))
            break

        placements = _extract_placements(built, solver, grid, sessions)
        results.append(SolveResult(status=status, placements=placements, infeasible_sessions=[]))

        if i < variant_count - 1:
            true_vars = [v for v in all_vars if solver.Value(v)]
            built.model.Add(sum(true_vars) <= len(true_vars) - 1)

    return results
