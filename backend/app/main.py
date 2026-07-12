from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import activities, auth, export, school_years, solve, solver_settings, subjects, teachers, zones
from app.config import settings

app = FastAPI(title="Timetable Generator API")


@app.exception_handler(IntegrityError)
def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
    # Deleting a row that's still referenced elsewhere (e.g. a trinn that
    # still has classes) hits a foreign-key constraint -- surface that as a
    # clean 409 instead of a raw 500, for every route, not just new ones.
    return JSONResponse(
        status_code=409,
        content={"detail": "Kan ikke fullføre: dataene brukes fortsatt av noe annet."},
    )

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
app.include_router(zones.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
