"""Bulk school-setup import: a single JSON payload that creates a whole new
school year (periods, trinn/classes/class-groups, teachers, subjects/hour
allocations, activities) in one transaction. See app/api/routes/import_.py
for the validation/creation logic and .claude/skills/school-import/ for the
Claude Code skill that produces this JSON from a free-form description.

Every cross-reference inside the payload is a human-readable natural key
(teacher initials, subject short_code, a "ClassName" or "ClassName:group"
class_ref, trinn level as a plain int) rather than a database id, since ids
don't exist until this endpoint actually creates the rows.
"""

from datetime import time

from pydantic import BaseModel

from app.db.models.activity import ActivityType
from app.db.models.period import DayOfWeek


class PeriodImport(BaseModel):
    day_of_week: DayOfWeek
    period_number: int
    start_time: time
    end_time: time
    is_splittable: bool = False
    is_before_lunch: bool = False


class ClassImport(BaseModel):
    name: str
    """Must be unique across the WHOLE payload, not just within its trinn --
    a real limitation, safe in practice since Norwegian class names already
    bake in the trinn (8A/9A/10A)."""
    extra_groups: list[str] = []
    """e.g. ["half1", "half2"]. The "whole" group is created automatically
    and must not be listed here."""


class TrinnImport(BaseModel):
    level: int
    classes: list[ClassImport] = []


class TeacherImport(BaseModel):
    initials: str
    full_name: str


class HourAllocationImport(BaseModel):
    trinn_level: int
    weekly_hours: float


class SubjectImport(BaseModel):
    short_code: str
    name: str
    is_trinnfag: bool = False
    is_krov: bool = False
    uses_hall: bool = False
    avoid_consecutive: bool = False
    prefer_before_lunch: bool = False
    needs_consecutive_periods: bool = False
    prefer_early_periods: bool = False
    avoid_friday_afternoon: bool = False
    no_repeat_same_day: bool = False
    max_concurrent_sessions: int | None = None
    hour_allocations: list[HourAllocationImport] = []


class ActivityLegImport(BaseModel):
    class_ref: str | None = None
    """"9A" (-> its "whole" group), "9A:half1", or None for a TRINNFAG
    overflow group with no home class."""
    subject_code: str
    teacher_initials: list[str] = []


class ActivityImport(BaseModel):
    activity_type: ActivityType
    duration_minutes: int
    """Must be a positive multiple of 30 (half-hour ticks)."""
    occurrences_per_week: int
    notes: str | None = None
    legs: list[ActivityLegImport]


class SchoolImport(BaseModel):
    school_year_label: str
    periods: list[PeriodImport] = []
    trinn: list[TrinnImport] = []
    teachers: list[TeacherImport] = []
    subjects: list[SubjectImport] = []
    activities: list[ActivityImport] = []


class ImportIssue(BaseModel):
    path: str
    message: str


class ImportResultRead(BaseModel):
    school_year_id: int
    counts: dict[str, int]
    warnings: list[ImportIssue] = []
