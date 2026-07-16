from pydantic import BaseModel, ConfigDict


class SubjectCreate(BaseModel):
    school_year_id: int
    name: str
    short_code: str
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


class SubjectRead(SubjectCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class SubjectHourAllocationCreate(BaseModel):
    subject_id: int
    trinn_id: int
    weekly_hours: float


class SubjectHourAllocationRead(SubjectHourAllocationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
