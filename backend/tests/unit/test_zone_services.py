from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models.user import User
from app.db.models.zone import ZoneInvitation, ZoneInvitationStatus, ZoneMembership, ZoneRole
from app.services.zones import sync_zone_state_on_login


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _make_user(db_session, email: str, google_sub: str) -> User:
    user = User(google_sub=google_sub, email=email, name=email.split("@")[0])
    db_session.add(user)
    db_session.flush()
    return user


def test_brand_new_user_with_no_invitation_gets_a_personal_owned_zone(db_session):
    user = _make_user(db_session, "new@example.com", "sub-new")
    sync_zone_state_on_login(db_session, user)

    memberships = db_session.scalars(
        select(ZoneMembership).where(ZoneMembership.user_id == user.id)
    ).all()
    assert len(memberships) == 1
    assert memberships[0].role == ZoneRole.OWNER


def test_user_with_pending_invitation_joins_only_the_invited_zone(db_session):
    owner = _make_user(db_session, "owner@example.com", "sub-owner")
    sync_zone_state_on_login(db_session, owner)
    owner_zone_id = db_session.scalars(
        select(ZoneMembership).where(ZoneMembership.user_id == owner.id)
    ).first().zone_id

    invitee_email = "invitee@example.com"
    db_session.add(
        ZoneInvitation(
            zone_id=owner_zone_id,
            email=invitee_email,
            invited_by_user_id=owner.id,
            status=ZoneInvitationStatus.PENDING,
            created_at=_now(),
        )
    )
    db_session.commit()

    invitee = _make_user(db_session, invitee_email, "sub-invitee")
    sync_zone_state_on_login(db_session, invitee)

    memberships = db_session.scalars(
        select(ZoneMembership).where(ZoneMembership.user_id == invitee.id)
    ).all()
    assert len(memberships) == 1
    assert memberships[0].zone_id == owner_zone_id
    assert memberships[0].role == ZoneRole.MEMBER

    invitation = db_session.scalars(select(ZoneInvitation)).first()
    assert invitation.status == ZoneInvitationStatus.ACCEPTED
    assert invitation.accepted_at is not None


def test_revoked_invitation_is_not_auto_accepted(db_session):
    owner = _make_user(db_session, "owner2@example.com", "sub-owner2")
    sync_zone_state_on_login(db_session, owner)
    owner_zone_id = db_session.scalars(
        select(ZoneMembership).where(ZoneMembership.user_id == owner.id)
    ).first().zone_id

    invitee_email = "revoked@example.com"
    db_session.add(
        ZoneInvitation(
            zone_id=owner_zone_id,
            email=invitee_email,
            invited_by_user_id=owner.id,
            status=ZoneInvitationStatus.REVOKED,
            created_at=_now(),
        )
    )
    db_session.commit()

    invitee = _make_user(db_session, invitee_email, "sub-revoked")
    sync_zone_state_on_login(db_session, invitee)

    memberships = db_session.scalars(
        select(ZoneMembership).where(ZoneMembership.user_id == invitee.id)
    ).all()
    # Not auto-joined to the owner's zone; falls back to a personal zone.
    assert len(memberships) == 1
    assert memberships[0].zone_id != owner_zone_id
    assert memberships[0].role == ZoneRole.OWNER
