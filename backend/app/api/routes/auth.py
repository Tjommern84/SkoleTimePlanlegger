from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.auth.google_oauth import oauth
from app.auth.session import SESSION_COOKIE_NAME, create_session_token
from app.config import settings
from app.db.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(request: Request):
    redirect_uri = f"{settings.oauth_redirect_base_url}/auth/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback", name="auth_callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo")
    if userinfo is None or not userinfo.get("email"):
        raise HTTPException(400, "Google did not return an email address")

    email = userinfo["email"].lower()
    if email not in settings.allowed_emails_list:
        raise HTTPException(403, "This account is not authorized to use this app")

    user = db.scalars(select(User).where(User.google_sub == userinfo["sub"])).first()
    if user is None:
        user = User(google_sub=userinfo["sub"], email=email, name=userinfo.get("name", email))
        db.add(user)
    else:
        user.email = email
        user.name = userinfo.get("name", email)
    db.commit()

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
def me(user: User = Depends(get_current_user)):
    return {"email": user.email, "name": user.name}
