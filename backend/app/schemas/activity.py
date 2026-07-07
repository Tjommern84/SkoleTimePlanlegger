from pydantic import BaseModel, ConfigDict

from app.db.models.activity import ActivityType


class ActivityLegCreate(BaseModel):
    class_group_id: int | None = None
    subject_id: int
    teacher_ids: list[int] = []


class ActivityLegRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    class_group_id: int | None
    subject_id: int
    teacher_ids: list[int] = []


class ActivityCreate(BaseModel):
    school_year_id: int
    activity_type: ActivityType
    duration_ticks: int
    occurrences_per_week: int
    notes: str | None = None
    legs: list[ActivityLegCreate]


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    school_year_id: int
    activity_type: ActivityType
    duration_ticks: int
    occurrences_per_week: int
    notes: str | None = None
    legs: list[ActivityLegRead] = []
