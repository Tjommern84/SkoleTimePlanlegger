"""Independent re-implementation of every hard-constraint check, written
separately from model_builder.py's CP-SAT formulation on purpose: a bug in
the CP-SAT modeling must not be able to silently "validate itself". Used
both in tests and (later, Phase 4+) as a safety net on every generated and
manually-edited timetable.
"""

from dataclasses import dataclass

from app.solver.grid import TickGrid
from app.solver.types import SessionInstance, SubjectData, TeacherUnavailabilityData


@dataclass(frozen=True)
class Violation:
    kind: str
    message: str


def validate(
    grid: TickGrid,
    sessions: list[SessionInstance],
    placements: dict[str, int],
    subjects_by_id: dict[int, SubjectData],
    teacher_unavailabilities: list[TeacherUnavailabilityData],
    mutually_exclusive_group_pairs: list[tuple[int, int]] | None = None,
    max_concurrent_krov: int = 2,
) -> list[Violation]:
    mutually_exclusive_group_pairs = mutually_exclusive_group_pairs or []
    violations: list[Violation] = []

    sessions_by_key = {s.key: s for s in sessions}
    for key in sessions_by_key:
        if key not in placements:
            violations.append(Violation("unplaced_session", f"Session {key} has no placement"))

    teacher_occupancy: dict[tuple[int, int], list[str]] = {}
    class_group_occupancy: dict[tuple[int, int], list[str]] = {}
    krov_occupancy: dict[int, list[str]] = {}
    hall_occupancy: dict[int, list[str]] = {}

    for key, start in placements.items():
        session = sessions_by_key.get(key)
        if session is None:
            continue

        valid_starts = set(grid.valid_start_ticks(session.duration_ticks))
        if start not in valid_starts:
            violations.append(
                Violation(
                    "invalid_placement",
                    f"Session {key} placed at tick {start}, which is not a structurally "
                    f"valid start (crosses a day/lunch boundary or splits a non-splittable period)",
                )
            )

        if session.fixed_start_tick is not None and start != session.fixed_start_tick:
            violations.append(
                Violation(
                    "fixed_placement_violated",
                    f"Session {key} must start at fixed tick {session.fixed_start_tick}, "
                    f"got {start}",
                )
            )

        for t in range(start, start + session.duration_ticks):
            for leg in session.legs:
                subject = subjects_by_id[leg.subject_id]
                for teacher_id in leg.teacher_ids:
                    teacher_occupancy.setdefault((teacher_id, t), []).append(key)
                if leg.class_group_id is not None:
                    class_group_occupancy.setdefault((leg.class_group_id, t), []).append(key)
                if subject.is_krov:
                    krov_occupancy.setdefault(t, []).append(key)
                if subject.uses_hall:
                    hall_occupancy.setdefault(t, []).append(key)

    for (teacher_id, t), keys in teacher_occupancy.items():
        if len(keys) > 1:
            violations.append(
                Violation(
                    "teacher_double_booked",
                    f"Teacher {teacher_id} double-booked at tick {t}: sessions {keys}",
                )
            )

    for (class_group_id, t), keys in class_group_occupancy.items():
        if len(keys) > 1:
            violations.append(
                Violation(
                    "class_group_double_booked",
                    f"Class-group {class_group_id} double-booked at tick {t}: sessions {keys}",
                )
            )

    for t, keys in krov_occupancy.items():
        if len(keys) > max_concurrent_krov:
            violations.append(
                Violation(
                    "krov_cap_exceeded",
                    f"KROV cap ({max_concurrent_krov}) exceeded at tick {t}: sessions {keys}",
                )
            )
        if keys and hall_occupancy.get(t):
            violations.append(
                Violation(
                    "krov_during_hall_use",
                    f"KROV running at tick {t} while hall is in use: krov={keys}, "
                    f"hall={hall_occupancy[t]}",
                )
            )

    for unavail in teacher_unavailabilities:
        forbidden_ticks = set(
            grid.ticks_for_period_range(unavail.day_of_week, unavail.start_period, unavail.end_period)
        )
        for (teacher_id, t), keys in teacher_occupancy.items():
            if teacher_id == unavail.teacher_id and t in forbidden_ticks:
                violations.append(
                    Violation(
                        "teacher_unavailable",
                        f"Teacher {teacher_id} scheduled at tick {t} during a blocked window: {keys}",
                    )
                )

    all_class_groups = {cid for (cid, _t) in class_group_occupancy}
    for cid in all_class_groups:
        for day, p2_tick in grid.period2_tick.items():
            p3_tick = grid.period3_tick.get(day)
            if p3_tick is None:
                continue
            occupied_p2 = bool(class_group_occupancy.get((cid, p2_tick)))
            occupied_p3 = bool(class_group_occupancy.get((cid, p3_tick)))
            if occupied_p2 != occupied_p3:
                violations.append(
                    Violation(
                        "stranded_half_hour",
                        f"Class-group {cid} has a stranded half-hour on {day.value}: "
                        f"period2_occupied={occupied_p2}, period3_occupied={occupied_p3}",
                    )
                )

    for g1, g2 in mutually_exclusive_group_pairs:
        ticks = {t for (cid, t) in class_group_occupancy if cid in (g1, g2)}
        for t in ticks:
            if class_group_occupancy.get((g1, t)) and class_group_occupancy.get((g2, t)):
                violations.append(
                    Violation(
                        "whole_half_group_conflict",
                        f"Class-groups {g1} (whole) and {g2} (half) both active at tick {t}",
                    )
                )

    return violations
