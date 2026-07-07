from app.db.models.school_year import SchoolYear
from app.db.models.period import PeriodDefinition, DayOfWeek
from app.db.models.trinn_class import Trinn, SchoolClass, ClassGroup
from app.db.models.teacher import Teacher, TeacherUnavailability, TeacherSubjectQualification
from app.db.models.subject import Subject, SubjectHourAllocation
from app.db.models.activity import (
    Activity,
    ActivityLeg,
    ActivityLegTeacher,
    ActivityType,
)
from app.db.models.solver_settings import SolverSettings
from app.db.models.timetable import GeneratedTimetable, TimetableSlot
from app.db.models.user import User

__all__ = [
    "SchoolYear",
    "PeriodDefinition",
    "DayOfWeek",
    "Trinn",
    "SchoolClass",
    "ClassGroup",
    "Teacher",
    "TeacherUnavailability",
    "TeacherSubjectQualification",
    "Subject",
    "SubjectHourAllocation",
    "Activity",
    "ActivityLeg",
    "ActivityLegTeacher",
    "ActivityType",
    "SolverSettings",
    "GeneratedTimetable",
    "TimetableSlot",
    "User",
]
