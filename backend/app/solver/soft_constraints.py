"""Phase 3: weighted soft-preference objective terms, added on top of the
Phase 2 hard-constraint model. All weights come from SolverSettingsData so
the school can retune preferences without a code change.

Soft preferences implemented (see docs/domain-notes.md):
- KRØV: prefer only 1 concurrent session, even though up to 2 is allowed.
- 10th-trinn KRØV: prefer the settings-configured periods (default 3-4).
- Musikk: avoid two ordinally-consecutive periods for the same class.
- Matematikk: prefer before lunch.
- Mat&Helse: prefer starting at period 2 (so it lands in periods 2-3-4).
- Subject.prefer_early_periods: prefer periods 1-2 (e.g. Valgfag).
- Subject.avoid_friday_afternoon: prefer not landing after the Friday
  lunch boundary (e.g. Fremmedspraak/Sprak).

Consecutive-period adjacency is ordinal (period N and N+1 count as
consecutive even across the lunch gap), matching the hard-constraint rules
elsewhere in the solver.
"""

from ortools.sat.python import cp_model

from app.db.models.period import DayOfWeek
from app.solver.grid import TickGrid
from app.solver.model_builder import BuiltModel
from app.solver.types import SessionInstance, SolverSettingsData, SubjectData

_CONSECUTIVE_PERIOD_PAIRS = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6)]


def add_soft_objective(
    model: cp_model.CpModel,
    built: BuiltModel,
    grid: TickGrid,
    sessions: list[SessionInstance],
    subjects_by_id: dict[int, SubjectData],
    settings: SolverSettingsData,
    krov10_session_keys: set[str] | None = None,
) -> None:
    krov10_session_keys = krov10_session_keys or set()

    krov_tick_vars: dict[int, list[cp_model.IntVar]] = {}
    krov10_penalty_vars: list[cp_model.IntVar] = []
    matte_penalty_vars: list[cp_model.IntVar] = []
    mat_helse_penalty_vars: list[cp_model.IntVar] = []
    early_periods_penalty_vars: list[cp_model.IntVar] = []
    friday_afternoon_penalty_vars: list[cp_model.IntVar] = []
    musikk_class_tick_vars: dict[tuple[int, int], list[cp_model.IntVar]] = {}

    for session in sessions:
        session_vars = built.start_vars.get(session.key)
        if not session_vars:
            continue
        for s, var in session_vars.items():
            period_number = grid.ticks[s].period_number
            day = grid.ticks[s].day
            occupied_ticks = range(s, s + session.duration_ticks)

            for leg in session.legs:
                subject = subjects_by_id[leg.subject_id]

                if subject.is_krov:
                    for t in occupied_ticks:
                        krov_tick_vars.setdefault(t, []).append(var)
                    if session.key in krov10_session_keys and period_number not in settings.krov10_preferred_periods:
                        krov10_penalty_vars.append(var)

                if subject.avoid_consecutive and leg.class_group_id is not None:
                    for t in occupied_ticks:
                        musikk_class_tick_vars.setdefault((leg.class_group_id, t), []).append(var)

                if subject.prefer_before_lunch:
                    boundary = grid.lunch_boundary.get(day)
                    if boundary is not None and s >= boundary:
                        matte_penalty_vars.append(var)

                # "Prefer periods 2-3-4" is specifically a Mat&Helse
                # placement preference, not shared with Kunst og handverk
                # (which also sets needs_consecutive_periods) -- see
                # docs/domain-notes.md.
                if subject.short_code == "MH" and period_number != 2:
                    mat_helse_penalty_vars.append(var)

                if subject.prefer_early_periods and period_number not in (1, 2):
                    early_periods_penalty_vars.append(var)

                if subject.avoid_friday_afternoon and day == DayOfWeek.FRI:
                    boundary = grid.lunch_boundary.get(day)
                    if boundary is not None and s >= boundary:
                        friday_afternoon_penalty_vars.append(var)

    krov_overflow_vars: list[cp_model.IntVar] = []
    for t, tick_vars in krov_tick_vars.items():
        overflow = model.NewIntVar(0, 1, f"krov_overflow_{t}")
        model.Add(overflow >= sum(tick_vars) - 1)
        krov_overflow_vars.append(overflow)

    musikk_consecutive_vars: list[cp_model.IntVar] = []
    period_first_tick: dict[tuple, int] = {}
    for idx, info in enumerate(grid.ticks):
        key = (info.day, info.period_number)
        period_first_tick.setdefault(key, idx)

    class_groups_with_musikk = {cid for (cid, _t) in musikk_class_tick_vars}
    for cid in class_groups_with_musikk:
        for day in grid.day_range:
            for p, p_next in _CONSECUTIVE_PERIOD_PAIRS:
                t1 = period_first_tick.get((day, p))
                t2 = period_first_tick.get((day, p_next))
                if t1 is None or t2 is None:
                    continue
                vars1 = musikk_class_tick_vars.get((cid, t1), [])
                vars2 = musikk_class_tick_vars.get((cid, t2), [])
                if not vars1 or not vars2:
                    continue
                both = model.NewBoolVar(f"musikk_consec_{cid}_{day.value}_{p}")
                model.Add(both <= sum(vars1))
                model.Add(both <= sum(vars2))
                model.Add(both >= sum(vars1) + sum(vars2) - 1)
                musikk_consecutive_vars.append(both)

    objective_terms = []
    objective_terms += [(settings.weight_krov_prefer_one, v) for v in krov_overflow_vars]
    objective_terms += [(settings.weight_krov_prefer_one, v) for v in krov10_penalty_vars]
    objective_terms += [(settings.weight_musikk_spread, v) for v in musikk_consecutive_vars]
    objective_terms += [(settings.weight_matte_before_lunch, v) for v in matte_penalty_vars]
    objective_terms += [(settings.weight_mat_helse_placement, v) for v in mat_helse_penalty_vars]
    objective_terms += [(settings.weight_prefer_early_periods, v) for v in early_periods_penalty_vars]
    objective_terms += [(settings.weight_avoid_friday_afternoon, v) for v in friday_afternoon_penalty_vars]

    if objective_terms:
        model.Minimize(sum(weight * var for weight, var in objective_terms))
