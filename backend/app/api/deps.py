from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.session import SESSION_COOKIE_NAME, read_session_token
from app.db.base import get_db
from app.db.models.school_year import SchoolYear
from app.db.models.teacher import Teacher
from app.db.models.user import User
from app.db.models.zone import ZoneMembership, ZoneRole

__all__ = [
    "get_db",
    "get_current_user",
    "require_zone_header",
    "require_zone_owner_header",
    "zone_membership_for_school_year",
    "zone_membership_for_teacher",
]


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    email = read_session_token(token) if token else None
    if email is None:
        raise HTTPException(401, "Not authenticated")

    user = db.scalars(select(User).where(User.email == email)).first()
    if user is None:
        raise HTTPException(401, "Not authenticated")
    return user


def _membership_or_404(db: Session, zone_id: int, user: User) -> ZoneMembership:
    """404 (not 403) so we don't reveal whether a zone id even exists to a
    caller who isn't a member of it."""
    membership = db.scalars(
        select(ZoneMembership).where(
            ZoneMembership.zone_id == zone_id, ZoneMembership.user_id == user.id
        )
    ).first()
    if membership is None:
        raise HTTPException(404, "Zone not found")
    return membership


def require_zone_header(
    request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ZoneMembership:
    """For the handful of "root" endpoints with no existing resource id to
    derive the zone from (list/create school-years, list/create teachers).
    Every other zone-scoped route instead derives the zone from a resource
    id it already receives -- see zone_membership_for_school_year/_teacher
    below -- so it doesn't need this header at all (notably, the Excel
    export download is a plain browser navigation and can't send one).
    """
    raw = request.headers.get("X-Zone-Id")
    if raw is None:
        raise HTTPException(400, "X-Zone-Id header is required")
    try:
        zone_id = int(raw)
    except ValueError:
        raise HTTPException(400, "X-Zone-Id must be an integer") from None
    return _membership_or_404(db, zone_id, user)


def require_zone_owner_header(
    membership: ZoneMembership = Depends(require_zone_header),
) -> ZoneMembership:
    if membership.role != ZoneRole.OWNER:
        raise HTTPException(403, "Only the zone owner can perform this action")
    return membership


def zone_membership_for_school_year(db: Session, user: User, school_year_id: int) -> ZoneMembership:
    """Derives the zone from an existing school_year_id and verifies the
    caller is a member of it. 404s if the school year doesn't exist OR the
    caller isn't a member of its zone (same response either way, on purpose).
    """
    school_year = db.get(SchoolYear, school_year_id)
    if school_year is None:
        raise HTTPException(404, "School year not found")
    return _membership_or_404(db, school_year.zone_id, user)


def zone_membership_for_teacher(db: Session, user: User, teacher_id: int) -> ZoneMembership:
    """Same pattern, derived from teacher.zone_id directly (teachers belong
    to a zone, not a specific school year)."""
    teacher = db.get(Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(404, "Teacher not found")
    return _membership_or_404(db, teacher.zone_id, user)
