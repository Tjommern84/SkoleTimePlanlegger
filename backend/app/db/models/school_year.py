from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SchoolYear(Base):
    __tablename__ = "school_years"
    __table_args__ = (UniqueConstraint("zone_id", "label"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(20), nullable=False)
