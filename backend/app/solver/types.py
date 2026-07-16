"""Plain-data types shared across the solver package. Deliberately not
SQLAlchemy ORM objects: keeps grid/expand/model_builder/validator testable
in isolation and prevents the CP-SAT model code and the independent
validator from accidentally sharing (and both trusting) the same buggy
data-loading path.
"""

from dataclasses import dataclass

from app.db.models.period import DayOfWeek


@dataclass(frozen=True)
class LegData:
    class_group_id: int | None
    subject_id: int
    teacher_ids: tuple[int, ...]


@dataclass(frozen=True)
class ActivityData:
    id: int
    activity_type: str  # "NORMAL" / "SPLIT_PARALLEL" / "TRINNFAG"
    duration_ticks: int
    occurrences_per_week: int
    legs: tuple[LegData, ...]


@dataclass(frozen=True)
class SessionInstance:
    """One concrete weekly occurrence of an Activity that needs a start
    tick. All legs share a single start-time decision -- this is the whole
    mechanism behind co-teaching, split-class parallel sessions, and
    trinnfag whole-grade blocking (see docs/domain-notes.md).
    """

    key: str
    activity_id: int
    occurrence_index: int
    duration_ticks: int
    legs: tuple[LegData, ...]
    fixed_start_tick: int | None = None


@dataclass(frozen=True)
class SubjectData:
    id: int
    short_code: str
    is_krov: bool
    uses_hall: bool
    is_trinnfag: bool
    avoid_consecutive: bool
    prefer_before_lunch: bool
    needs_consecutive_periods: bool
    prefer_early_periods: bool
    avoid_friday_afternoon: bool
    no_repeat_same_day: bool
    max_concurrent_sessions: int | None


@dataclass(frozen=True)
class TeacherUnavailabilityData:
    teacher_id: int
    day_of_week: DayOfWeek
    start_period: int | None
    end_period: int | None


@dataclass(frozen=True)
class SolverSettingsData:
    max_concurrent_krov: int
    preferred_concurrent_krov: int
    krov10_preferred_periods: tuple[int, ...]
    weight_musikk_spread: int
    weight_matte_before_lunch: int
    weight_mat_helse_placement: int
    weight_krov_prefer_one: int
    weight_prefer_early_periods: int
    weight_avoid_friday_afternoon: int
