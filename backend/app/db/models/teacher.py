from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.period import DayOfWeek


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    initials: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)


class TeacherUnavailability(Base):
    """A blocked window for a part-time/studying teacher. If start_period and
    end_period are both null, the entire day is blocked; otherwise only that
    inclusive ordinal period range is blocked.
    """

    __tablename__ = "teacher_unavailabilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), nullable=False)
    school_year_id: Mapped[int] = mapped_column(ForeignKey("school_years.id"), nullable=False)
    day_of_week: Mapped[DayOfWeek] = mapped_column(Enum(DayOfWeek), nullable=False)
    start_period: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_period: Mapped[int | None] = mapped_column(Integer, nullable=True)


class TeacherSubjectQualification(Base):
    """Which subjects a teacher can/does teach, with a generic weekly-hours
    figure -- NOT tied to a specific class. This is overview metadata for
    the Teachers page; it does not feed the solver, which instead derives
    actual per-class teaching load from Activity/ActivityLeg records (see
    docs/domain-notes.md). A full teacher<->class activity-matrix editor
    is a separate, larger future feature.
    """

    __tablename__ = "teacher_subject_qualifications"
    __table_args__ = (UniqueConstraint("teacher_id", "subject_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    weekly_hours: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
