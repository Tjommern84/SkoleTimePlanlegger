import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ZoneRole(enum.Enum):
    OWNER = "owner"
    MEMBER = "member"


class ZoneInvitationStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"


class Zone(Base):
    """A user's isolated workspace. School years and teachers belong to
    exactly one zone; everything else (activities, subjects, generated
    timetables, ...) inherits zone scoping transitively through those.
    """

    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ZoneMembership(Base):
    __tablename__ = "zone_memberships"
    __table_args__ = (UniqueConstraint("zone_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[ZoneRole] = mapped_column(Enum(ZoneRole), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ZoneInvitation(Base):
    """Auto-accepted the next time `email` logs in via Google -- see
    app/services/zones.py:sync_zone_state_on_login. No email is sent by
    this app; the owner communicates the invite out of band. `email` is
    always stored lowercased to match User.email.
    """

    __tablename__ = "zone_invitations"
    __table_args__ = (Index("ix_zone_invitations_email_status", "email", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    invited_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[ZoneInvitationStatus] = mapped_column(
        Enum(ZoneInvitationStatus), nullable=False, default=ZoneInvitationStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
