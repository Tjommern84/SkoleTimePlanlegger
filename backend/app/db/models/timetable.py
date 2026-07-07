from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.period import DayOfWeek


class GeneratedTimetable(Base):
    __tablename__ = "generated_timetables"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_year_id: Mapped[int] = mapped_column(ForeignKey("school_years.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    solver_status: Mapped[str] = mapped_column(String(20), nullable=False)  # OPTIMAL/FEASIBLE/INFEASIBLE
    objective_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class TimetableSlot(Base):
    """One placed occurrence of an Activity. All legs (class-groups/teachers)
    are implied via activity_id -> ActivityLeg. start_tick is a half-hour
    tick index within the day (0-based); duration_ticks is the length.
    Directly editable post-solve for manual adjustment.
    """

    __tablename__ = "timetable_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    generated_timetable_id: Mapped[int] = mapped_column(
        ForeignKey("generated_timetables.id"), nullable=False
    )
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"), nullable=False)
    occurrence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    day_of_week: Mapped[DayOfWeek] = mapped_column(Enum(DayOfWeek), nullable=False)
    start_tick: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ticks: Mapped[int] = mapped_column(Integer, nullable=False)
