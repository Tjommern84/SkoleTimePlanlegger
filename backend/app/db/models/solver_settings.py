from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SolverSettings(Base):
    """Single editable row per school year -- tunable without a code change.
    Hall exclusivity scope (school-wide, gated by Subject.uses_hall) is a
    fixed rule, not represented here.
    """

    __tablename__ = "solver_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_year_id: Mapped[int] = mapped_column(ForeignKey("school_years.id"), unique=True, nullable=False)

    max_concurrent_krov: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    preferred_concurrent_krov: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # Comma-separated ordinal period numbers, e.g. "3,4"
    krov10_preferred_periods: Mapped[str] = mapped_column(String(50), default="3,4", nullable=False)
    fremmedspraak10_fixed_day: Mapped[str] = mapped_column(String(3), default="WED", nullable=False)
    fremmedspraak10_fixed_periods: Mapped[str] = mapped_column(String(50), default="5,6", nullable=False)

    weight_musikk_spread: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    weight_matte_before_lunch: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    weight_mat_helse_placement: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    weight_krov_prefer_one: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    weight_prefer_early_periods: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    weight_avoid_friday_afternoon: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
