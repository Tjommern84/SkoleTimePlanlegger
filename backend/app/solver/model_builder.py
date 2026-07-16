"""Builds the CP-SAT model for hard constraints only (Phase 2). Soft
constraints/optimization objective are added on top in Phase 3.

Uses a time-indexed boolean formulation (see docs/domain-notes.md): one
start[key, s] boolean per SessionInstance per valid start tick, with
resource occupancy expressed as linear sums over the relevant start vars
rather than as separate occupancy variables.
"""

from dataclasses import dataclass

from ortools.sat.python import cp_model

from app.solver.grid import TickGrid
from app.solver.types import SessionInstance, SubjectData, TeacherUnavailabilityData

StartVars = dict[str, dict[int, cp_model.IntVar]]


@dataclass
class BuiltModel:
    model: cp_model.CpModel
    start_vars: StartVars
    infeasible_sessions: list[str]  # session keys with zero valid start ticks


def build_model(
    grid: TickGrid,
    sessions: list[SessionInstance],
    subjects_by_id: dict[int, SubjectData],
    teacher_unavailabilities: list[TeacherUnavailabilityData],
    mutually_exclusive_group_pairs: list[tuple[int, int]] | None = None,
    max_concurrent_krov: int = 2,
) -> BuiltModel:
    model = cp_model.CpModel()
    mutually_exclusive_group_pairs = mutually_exclusive_group_pairs or []

    start_vars: StartVars = {}
    infeasible_sessions: list[str] = []

    teacher_tick_vars: dict[tuple[int, int], list[cp_model.IntVar]] = {}
    class_group_tick_vars: dict[tuple[int, int], list[cp_model.IntVar]] = {}
    krov_tick_vars: dict[int, list[cp_model.IntVar]] = {}
    hall_tick_vars: dict[int, list[cp_model.IntVar]] = {}
    subject_tick_vars: dict[tuple[int, int], list[cp_model.IntVar]] = {}
    # (class_group_id, subject_id, day) -> this session's "did it land on
    # this day" indicator, only for subjects with no_repeat_same_day set.
    no_repeat_same_day_terms: dict[tuple[int, int, object], list] = {}

    for session in sessions:
        valid_starts = grid.valid_start_ticks(session.duration_ticks)
        if session.fixed_start_tick is not None:
            valid_starts = [s for s in valid_starts if s == session.fixed_start_tick]

        if not valid_starts:
            infeasible_sessions.append(session.key)
            continue

        session_vars = {
            s: model.NewBoolVar(f"start[{session.key},{s}]") for s in valid_starts
        }
        start_vars[session.key] = session_vars
        model.AddExactlyOne(session_vars.values())

        for s, var in session_vars.items():
            occupied_ticks = range(s, s + session.duration_ticks)
            for leg in session.legs:
                subject = subjects_by_id[leg.subject_id]
                for t in occupied_ticks:
                    for teacher_id in leg.teacher_ids:
                        teacher_tick_vars.setdefault((teacher_id, t), []).append(var)
                    if leg.class_group_id is not None:
                        class_group_tick_vars.setdefault((leg.class_group_id, t), []).append(var)
                    if subject.is_krov:
                        krov_tick_vars.setdefault(t, []).append(var)
                    if subject.uses_hall:
                        hall_tick_vars.setdefault(t, []).append(var)
                    if subject.max_concurrent_sessions is not None:
                        subject_tick_vars.setdefault((subject.id, t), []).append(var)

    if infeasible_sessions:
        # Still return a model so callers can decide how to surface this;
        # building constraints over an empty/partial session set is safe.
        pass

    # Per-session "did it land on day D" indicators for the opt-in
    # no_repeat_same_day HARD rule. Sessions shorter than a full period
    # (single 30-min ticks) are exempt: those are the intentional
    # half-hour-adjacency pairing mechanism (two different teachers each
    # solo-covering half of a subject's weekly remainder), which
    # legitimately wants to land on the same day so the halves can satisfy
    # the period-2/period-3 adjacency rule together.
    for session in sessions:
        if session.duration_ticks < 2:
            continue
        session_vars = start_vars.get(session.key)
        if not session_vars:
            continue
        vars_by_day: dict[object, list] = {}
        for s, var in session_vars.items():
            vars_by_day.setdefault(grid.ticks[s].day, []).append(var)
        for leg in session.legs:
            if leg.class_group_id is None:
                continue
            subject = subjects_by_id[leg.subject_id]
            if not subject.no_repeat_same_day:
                continue
            for day, day_vars in vars_by_day.items():
                # AddExactlyOne over ALL of this session's start ticks means
                # sum(day_vars) is already 0-or-1 -- this session's own
                # "did it land on this day" indicator, no new var needed.
                no_repeat_same_day_terms.setdefault(
                    (leg.class_group_id, leg.subject_id, day), []
                ).append(sum(day_vars))

    for _, tick_vars in teacher_tick_vars.items():
        model.Add(sum(tick_vars) <= 1)

    for _, tick_vars in class_group_tick_vars.items():
        model.Add(sum(tick_vars) <= 1)

    for t, tick_vars in krov_tick_vars.items():
        model.Add(sum(tick_vars) <= max_concurrent_krov)

    # Generic per-subject school-wide concurrency cap (e.g. limited science
    # lab capacity for Naturfag) -- independent of the KRØV/hall mechanism.
    for (subject_id, _t), tick_vars in subject_tick_vars.items():
        cap = subjects_by_id[subject_id].max_concurrent_sessions
        if cap is not None:
            model.Add(sum(tick_vars) <= cap)

    for _, terms in no_repeat_same_day_terms.items():
        model.Add(sum(terms) <= 1)

    # Hall exclusivity, school-wide, gated by Subject.uses_hall (NOT all
    # trinnfag -- Valgfag uses the hall, Fremmedspraak does not).
    for t in set(krov_tick_vars) | set(hall_tick_vars):
        for krov_var in krov_tick_vars.get(t, []):
            for hall_var in hall_tick_vars.get(t, []):
                model.Add(krov_var + hall_var <= 1)

    # Teacher unavailability.
    for unavail in teacher_unavailabilities:
        for t in grid.ticks_for_period_range(
            unavail.day_of_week, unavail.start_period, unavail.end_period
        ):
            for var in teacher_tick_vars.get((unavail.teacher_id, t), []):
                model.Add(var == 0)

    # Half-hour adjacency: for every class-group, period-2 and period-3
    # occupancy must match (both empty or both occupied) on any given day
    # -- see docs/domain-notes.md for the derivation of this rule.
    all_class_groups = {cid for (cid, _t) in class_group_tick_vars}
    for cid in all_class_groups:
        for day, p2_tick in grid.period2_tick.items():
            p3_tick = grid.period3_tick.get(day)
            if p3_tick is None:
                continue
            p2_vars = class_group_tick_vars.get((cid, p2_tick), [])
            p3_vars = class_group_tick_vars.get((cid, p3_tick), [])
            if not p2_vars and not p3_vars:
                continue
            model.Add(sum(p2_vars) == sum(p3_vars))

    # A class's "whole" group and its half-groups (half1/half2) represent
    # the same students -- they must never both be active at once, even
    # though half1 and half2 legitimately run in parallel with each other.
    for g1, g2 in mutually_exclusive_group_pairs:
        ticks = {t for (cid, t) in class_group_tick_vars if cid in (g1, g2)}
        for t in ticks:
            vars1 = class_group_tick_vars.get((g1, t), [])
            vars2 = class_group_tick_vars.get((g2, t), [])
            model.Add(sum(vars1) + sum(vars2) <= 1)

    return BuiltModel(model=model, start_vars=start_vars, infeasible_sessions=infeasible_sessions)
