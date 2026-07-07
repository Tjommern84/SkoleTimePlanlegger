from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import activities, auth, export, school_years, solve, solver_settings, subjects, teachers
from app.config import settings

app = FastAPI(title="Timetable Generator API")

# Frontend (Vercel) and backend (Render) are separate origins in
# production, so the browser needs explicit CORS permission -- with
# credentials, since auth relies on a session cookie, not a bearer token.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Needed by Authlib to stash OAuth state/nonce during the Google login
# handshake -- distinct from our own signed app-session cookie (see
# app/auth/session.py, cookie name "session"), which represents "who is
# logged in" afterward. Explicit cookie name to avoid colliding with that
# cookie -- Starlette's default session_cookie is also "session".
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="oauth_state",
    same_site="none" if settings.is_production else "lax",
    https_only=settings.is_production,
)

app.include_router(auth.router)
app.include_router(school_years.router)
app.include_router(teachers.router)
app.include_router(subjects.router)
app.include_router(activities.router)
app.include_router(solver_settings.router)
app.include_router(solve.router)
app.include_router(export.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
