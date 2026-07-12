"""Zone provisioning/invitation-acceptance run on every login. Kept out of
app/api/routes/auth.py so it can be unit-tested without exercising the
Google OAuth handshake.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.db.models.zone import Zone, ZoneInvitation, ZoneInvitationStatus, ZoneMembership, ZoneRole


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def accept_pending_invitations(db: Session, user: User) -> list[ZoneMembership]:
    """Converts every pending invitation addressed to `user`'s email into a
    membership, marking each invitation accepted. Returns the newly created
    memberships.
    """
    pending = db.scalars(
        select(ZoneInvitation).where(
            ZoneInvitation.status == ZoneInvitationStatus.PENDING,
            ZoneInvitation.email == user.email.lower(),
        )
    ).all()

    created: list[ZoneMembership] = []
    for invitation in pending:
        existing = db.scalars(
            select(ZoneMembership).where(
                ZoneMembership.zone_id == invitation.zone_id, ZoneMembership.user_id == user.id
            )
        ).first()
        if existing is None:
            membership = ZoneMembership(
                zone_id=invitation.zone_id, user_id=user.id, role=ZoneRole.MEMBER, created_at=_now()
            )
            db.add(membership)
            created.append(membership)
        invitation.status = ZoneInvitationStatus.ACCEPTED
        invitation.accepted_at = _now()
    return created


def ensure_owner_zone_if_none(db: Session, user: User) -> ZoneMembership | None:
    """Creates a brand-new personal zone (owned by `user`) only if they have
    zero memberships at all. Must be called AFTER accept_pending_invitations
    in the same transaction, so a user invited before their first login ends
    up only in the zone(s) they were invited to, never an extra empty one.
    """
    has_membership = (
        db.scalars(select(ZoneMembership).where(ZoneMembership.user_id == user.id)).first()
        is not None
    )
    if has_membership:
        return None

    zone = Zone(name=f"{user.name}s sone", created_at=_now())
    db.add(zone)
    db.flush()
    membership = ZoneMembership(zone_id=zone.id, user_id=user.id, role=ZoneRole.OWNER, created_at=_now())
    db.add(membership)
    return membership


def sync_zone_state_on_login(db: Session, user: User) -> None:
    """Call once per successful login, after the User row itself is
    committed/flushed with an id."""
    accept_pending_invitations(db, user)
    ensure_owner_zone_if_none(db, user)
    db.commit()
