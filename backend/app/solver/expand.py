from app.solver.types import ActivityData, SessionInstance


def expand_activities(
    activities: list[ActivityData], fixed_placements: dict[int, int] | None = None
) -> list[SessionInstance]:
    """One SessionInstance per weekly occurrence of each Activity.
    fixed_placements optionally maps activity_id -> a required start tick
    (e.g. 10th-trinn Fremmedspraak's fixed Wednesday periods 5-6 slot).
    """
    fixed_placements = fixed_placements or {}
    instances: list[SessionInstance] = []
    for activity in activities:
        fixed = fixed_placements.get(activity.id)
        for occurrence_index in range(activity.occurrences_per_week):
            instances.append(
                SessionInstance(
                    key=f"{activity.id}#{occurrence_index}",
                    activity_id=activity.id,
                    occurrence_index=occurrence_index,
                    duration_ticks=activity.duration_ticks,
                    legs=activity.legs,
                    fixed_start_tick=fixed,
                )
            )
    return instances
