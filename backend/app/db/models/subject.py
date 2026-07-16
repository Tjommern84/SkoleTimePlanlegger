from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("school_year_id", "short_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    school_year_id: Mapped[int] = mapped_column(ForeignKey("school_years.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    short_code: Mapped[str] = mapped_column(String(20), nullable=False)
    is_trinnfag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_krov: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Drives school-wide KRØV blocking. True for valgfag, False for
    # fremmedspråk, independent of is_trinnfag -- do not derive from it.
    uses_hall: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    avoid_consecutive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    prefer_before_lunch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    needs_consecutive_periods: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    prefer_early_periods: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    avoid_friday_afternoon: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # HARD rule: this subject can never occur twice in the same day for the
    # same class -- opt-in per subject (not universal) since some subjects
    # (e.g. Musikk's avoid_consecutive) deliberately allow twice-a-day as
    # long as the two sessions aren't adjacent periods. A universal version
    # of this rule was tried and reverted -- see docs/domain-notes.md.
    no_repeat_same_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # HARD cap: at most this many concurrent sessions of this subject may
    # run anywhere in the school at once (school-wide, not per-class) --
    # e.g. limited science-lab capacity. Null = no cap. Independent of the
    # is_krov/uses_hall mechanism (which is specific to gym/hall exclusivity).
    max_concurrent_sessions: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SubjectHourAllocation(Base):
    __tablename__ = "subject_hour_allocations"
    __table_args__ = (UniqueConstraint("subject_id", "trinn_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    trinn_id: Mapped[int] = mapped_column(ForeignKey("trinn.id"), nullable=False)
    weekly_hours: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
