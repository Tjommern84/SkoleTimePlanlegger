import enum

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DayOfWeek(enum.Enum):
    MON = "MON"
    TUE = "TUE"
    WED = "WED"
    THU = "THU"
    FRI = "FRI"


class PeriodDefinition(Base):
    """Wall-clock config for one period on one weekday. Decoupled from solver
    ordinals: the solver only reasons in (day_of_week, period_number) pairs,
    so period 3 and 4 count as consecutive even though start_time/end_time
    has a lunch gap between them.
    """

    __tablename__ = "period_definitions"
    __table_args__ = (UniqueConstraint("school_year_id", "day_of_week", "period_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    school_year_id: Mapped[int] = mapped_column(ForeignKey("school_years.id"), nullable=False)
    day_of_week: Mapped[DayOfWeek] = mapped_column(Enum(DayOfWeek), nullable=False)
    period_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[object] = mapped_column(Time, nullable=False)
    end_time: Mapped[object] = mapped_column(Time, nullable=False)
    is_splittable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_before_lunch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
