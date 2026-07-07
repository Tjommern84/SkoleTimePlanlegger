from pydantic import BaseModel, ConfigDict

from app.db.models.period import DayOfWeek


class TeacherCreate(BaseModel):
    initials: str
    full_name: str


class TeacherRead(TeacherCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class TeacherUnavailabilityCreate(BaseModel):
    teacher_id: int
    school_year_id: int
    day_of_week: DayOfWeek
    start_period: int | None = None
    end_period: int | None = None


class TeacherUnavailabilityRead(TeacherUnavailabilityCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class TeacherSubjectQualificationCreate(BaseModel):
    teacher_id: int
    subject_id: int
    weekly_hours: float | None = None


class TeacherSubjectQualificationUpdate(BaseModel):
    weekly_hours: float | None = None


class TeacherSubjectQualificationRead(TeacherSubjectQualificationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
