from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Trinn(Base):
    __tablename__ = "trinn"
    __table_args__ = (UniqueConstraint("school_year_id", "level"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    school_year_id: Mapped[int] = mapped_column(ForeignKey("school_years.id"), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)  # 8, 9, or 10


class SchoolClass(Base):
    __tablename__ = "school_classes"
    __table_args__ = (UniqueConstraint("trinn_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    trinn_id: Mapped[int] = mapped_column(ForeignKey("trinn.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(20), nullable=False)  # "8A"


class ClassGroup(Base):
    """Solver's actual resource granularity. A class normally has one
    ClassGroup labelled 'whole'; split-class activities (e.g. half doing
    Mat&Helse while the other half does Naturfag) use 'half1'/'half2'.
    """

    __tablename__ = "class_groups"
    __table_args__ = (UniqueConstraint("school_class_id", "label"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    school_class_id: Mapped[int] = mapped_column(ForeignKey("school_classes.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(20), nullable=False)  # "whole" / "half1" / "half2"
