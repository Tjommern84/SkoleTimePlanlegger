import enum

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ActivityType(enum.Enum):
    NORMAL = "NORMAL"
    SPLIT_PARALLEL = "SPLIT_PARALLEL"
    TRINNFAG = "TRINNFAG"


class Activity(Base):
    """A weekly recurring pattern to place on the timetable, e.g. '8B Norsk
    co-taught (LEN+GB), 3x/week'. Fractional weekly subject hours are
    decomposed into one or more Activity rows by the user (or a seeded
    default), not automatically by the solver.

    Subject lives on ActivityLeg, not here: SPLIT_PARALLEL and TRINNFAG
    activities place two-or-more *different* subjects in the same shared
    time slot (e.g. one half of 9A does Mat&Helse while the other half does
    Naturfag; a trinnfag block runs Tysk/Fransk/Spansk as parallel groups),
    so a single subject_id on the Activity itself can't represent that.
    """

    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    school_year_id: Mapped[int] = mapped_column(ForeignKey("school_years.id"), nullable=False)
    activity_type: Mapped[ActivityType] = mapped_column(Enum(ActivityType), nullable=False)
    # Half-hour tick units -- 1 tick = 30 min, since periods 2/3 are 30 min
    # while periods 1/4/5/6 are 60 min each. A 60-min session = 2 ticks.
    duration_ticks: Mapped[int] = mapped_column(Integer, nullable=False)
    occurrences_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    legs: Mapped[list["ActivityLeg"]] = relationship(
        back_populates="activity", cascade="all, delete-orphan"
    )


class ActivityLeg(Base):
    """One participating (class-group, subject) pair in an Activity, sharing
    the Activity's single start-time decision in the solver. NORMAL
    activities have exactly one leg; SPLIT_PARALLEL has two; TRINNFAG has N
    (one per parallel subject-group).

    class_group_id is nullable to cover trinnfag activities where the
    number of parallel subject-groups (e.g. valgfag groups TS/AS/AT/ER)
    exceeds the number of home classes in the trinn (e.g. 3 classes): the
    home classes get ordinary legs (class_group_id set) to mark their
    students busy, and any *extra* teacher-led groups beyond that get a
    class_group_id=None leg that only occupies its teacher resource(s),
    since those students aren't tied to a single home class for this block.
    """

    __tablename__ = "activity_legs"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id"), nullable=False)
    class_group_id: Mapped[int | None] = mapped_column(ForeignKey("class_groups.id"), nullable=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)

    activity: Mapped["Activity"] = relationship(back_populates="legs")
    leg_teachers: Mapped[list["ActivityLegTeacher"]] = relationship(
        back_populates="leg", cascade="all, delete-orphan"
    )


class ActivityLegTeacher(Base):
    """Join table: supports multiple co-teachers on a single leg."""

    __tablename__ = "activity_leg_teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_leg_id: Mapped[int] = mapped_column(ForeignKey("activity_legs.id"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), nullable=False)

    leg: Mapped["ActivityLeg"] = relationship(back_populates="leg_teachers")
