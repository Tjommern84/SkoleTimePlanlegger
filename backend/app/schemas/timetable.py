from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models.period import DayOfWeek


class TimetableSlotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    activity_id: int
    occurrence_index: int
    day_of_week: DayOfWeek
    start_tick: int
    duration_ticks: int


class GeneratedTimetableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    school_year_id: int
    created_at: datetime
    solver_status: str
    objective_value: float | None
    is_active: bool
    slots: list[TimetableSlotRead] = []
