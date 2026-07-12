from authlib.integrations.base_client.errors import OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.auth.google_oauth import oauth
from app.auth.session import SESSION_COOKIE_NAME, create_session_token
from app.config import settings
from app.db.models.user import User
from app.db.models.zone import Zone, ZoneMembership
from app.services.zones import sync_zone_state_on_login

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(request: Request):
    redirect_uri = f"{settings.oauth_redirect_base_url}/auth/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback", name="auth_callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        # The authorization code is single-use and short-lived. Reloading
        # this exact URL (e.g. a browser "request desktop site" refresh, a
        # duplicate tab, or navigating back/forward through history) resends
        # an already-consumed or expired code, which Google rejects -- bounce
        # back to login instead of leaking a raw 500.
        return RedirectResponse(url=settings.frontend_url)
    userinfo = token.get("userinfo")
    if userinfo is None or not userinfo.get("email"):
        raise HTTPException(400, "Google did not return an email address")

    email = userinfo["email"].lower()

    user = db.scalars(select(User).where(User.google_sub == userinfo["sub"])).first()
    if user is None:
        user = User(google_sub=userinfo["sub"], email=email, name=userinfo.get("name", email))
        db.add(user)
    else:
        user.email = email
        user.name = userinfo.get("name", email)
    db.commit()
    db.refresh(user)

    sync_zone_state_on_login(db, user)

    response = RedirectResponse(url=settings.frontend_url)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        create_session_token(email),
        httponly=True,
        # Cross-site (Vercel <-> Render) requires SameSite=None + Secure;
        # locally over http, SameSite=Lax is simpler and sufficient.
        samesite="none" if settings.is_production else "lax",
        secure=settings.is_production,
        max_age=60 * 60 * 24 * 30,
    )
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse(url=settings.frontend_url)
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        samesite="none" if settings.is_production else "lax",
        secure=settings.is_production,
    )
    return response


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(ZoneMembership, Zone)
        .join(Zone, Zone.id == ZoneMembership.zone_id)
        .where(ZoneMembership.user_id == user.id)
    ).all()
    return {
        "email": user.email,
        "name": user.name,
        "zones": [{"id": zone.id, "name": zone.name, "role": m.role.value} for m, zone in rows],
    }
