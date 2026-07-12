from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_zone_header, require_zone_owner_header
from app.db.models.user import User
from app.db.models.zone import Zone, ZoneInvitation, ZoneInvitationStatus, ZoneMembership, ZoneRole
from app.schemas.zone import ZoneInvitationCreate, ZoneInvitationRead, ZoneMemberRead, ZoneRename

router = APIRouter(prefix="/api/zones", tags=["zones"])


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.patch("/current")
def rename_zone(
    payload: ZoneRename, db: Session = Depends(get_db), membership: ZoneMembership = Depends(require_zone_owner_header)
):
    zone = db.get(Zone, membership.zone_id)
    zone.name = payload.name
    db.commit()
    return {"id": zone.id, "name": zone.name}


@router.get("/current/members", response_model=list[ZoneMemberRead])
def list_members(db: Session = Depends(get_db), membership: ZoneMembership = Depends(require_zone_header)):
    rows = db.execute(
        select(ZoneMembership, User)
        .join(User, User.id == ZoneMembership.user_id)
        .where(ZoneMembership.zone_id == membership.zone_id)
    ).all()
    return [
        ZoneMemberRead(
            user_id=user.id, email=user.email, name=user.name, role=m.role.value, joined_at=m.created_at
        )
        for m, user in rows
    ]


@router.post("/current/invitations", response_model=ZoneInvitationRead, status_code=201)
def create_invitation(
    payload: ZoneInvitationCreate,
    db: Session = Depends(get_db),
    membership: ZoneMembership = Depends(require_zone_owner_header),
):
    already_member = db.execute(
        select(ZoneMembership)
        .join(User, User.id == ZoneMembership.user_id)
        .where(ZoneMembership.zone_id == membership.zone_id, User.email == payload.email)
    ).first()
    if already_member is not None:
        raise HTTPException(400, "This email is already a member of the zone")

    existing_pending = db.scalars(
        select(ZoneInvitation).where(
            ZoneInvitation.zone_id == membership.zone_id,
            ZoneInvitation.email == payload.email,
            ZoneInvitation.status == ZoneInvitationStatus.PENDING,
        )
    ).first()
    if existing_pending is not None:
        raise HTTPException(409, "There is already a pending invitation for this email")

    invitation = ZoneInvitation(
        zone_id=membership.zone_id,
        email=payload.email,
        invited_by_user_id=membership.user_id,
        status=ZoneInvitationStatus.PENDING,
        created_at=_now(),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


@router.get("/current/invitations", response_model=list[ZoneInvitationRead])
def list_invitations(
    db: Session = Depends(get_db), membership: ZoneMembership = Depends(require_zone_owner_header)
):
    stmt = (
        select(ZoneInvitation)
        .where(ZoneInvitation.zone_id == membership.zone_id)
        .order_by(ZoneInvitation.created_at.desc())
    )
    return db.scalars(stmt).all()


@router.delete("/current/invitations/{invitation_id}", status_code=204)
def revoke_invitation(
    invitation_id: int,
    db: Session = Depends(get_db),
    membership: ZoneMembership = Depends(require_zone_owner_header),
):
    invitation = db.scalars(
        select(ZoneInvitation).where(
            ZoneInvitation.id == invitation_id, ZoneInvitation.zone_id == membership.zone_id
        )
    ).first()
    if invitation is None:
        raise HTTPException(404, "Invitation not found")
    invitation.status = ZoneInvitationStatus.REVOKED
    db.commit()


@router.delete("/current/members/{user_id}", status_code=204)
def remove_member(
    user_id: int,
    db: Session = Depends(get_db),
    membership: ZoneMembership = Depends(require_zone_owner_header),
):
    target = db.scalars(
        select(ZoneMembership).where(
            ZoneMembership.zone_id == membership.zone_id, ZoneMembership.user_id == user_id
        )
    ).first()
    if target is None:
        raise HTTPException(404, "Member not found")

    if target.role == ZoneRole.OWNER:
        other_owners = db.scalars(
            select(ZoneMembership).where(
                ZoneMembership.zone_id == membership.zone_id,
                ZoneMembership.role == ZoneRole.OWNER,
                ZoneMembership.user_id != user_id,
            )
        ).first()
        if other_owners is None:
            raise HTTPException(400, "Cannot remove the zone's last remaining owner")

    db.delete(target)
    db.commit()
