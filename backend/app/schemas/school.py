from datetime import time

from pydantic import BaseModel, ConfigDict

from app.db.models.period import DayOfWeek


class SchoolYearCreate(BaseModel):
    label: str


class SchoolYearRead(SchoolYearCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class PeriodDefinitionCreate(BaseModel):
    school_year_id: int
    day_of_week: DayOfWeek
    period_number: int
    start_time: time
    end_time: time
    is_splittable: bool = False
    is_before_lunch: bool = False


class PeriodDefinitionRead(PeriodDefinitionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class TrinnCreate(BaseModel):
    school_year_id: int
    level: int


class TrinnRead(TrinnCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class SchoolClassCreate(BaseModel):
    trinn_id: int
    name: str


class SchoolClassRead(SchoolClassCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ClassGroupCreate(BaseModel):
    school_class_id: int
    label: str = "whole"


class ClassGroupRead(ClassGroupCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
