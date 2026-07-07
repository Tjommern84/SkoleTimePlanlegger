from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./timetable.db"
    google_client_id: str = ""
    google_client_secret: str = ""
    # Fixed, not derived from the incoming request: must exactly match an
    # Authorized redirect URI registered in Google Cloud Console. Deriving
    # it from request.url_for() is fragile -- it reflects whatever
    # host/port the request happened to arrive on (e.g. 127.0.0.1 vs
    # localhost, or a dev proxy's upstream target), which silently breaks
    # the OAuth callback with a redirect_uri_mismatch error from Google.
    oauth_redirect_base_url: str = "http://localhost:8123"
    # Where to send the browser after login/logout. In local dev the
    # frontend runs on its own Vite port, separate from the backend --
    # redirecting to "/" would hit the backend itself and 404. In
    # production, where FastAPI serves the built frontend from the same
    # origin, this should be set to "/" instead.
    frontend_url: str = "http://localhost:5173"
    allowed_emails: str = ""
    session_secret: str = "dev-secret-change-me"

    # Frontend and backend are deployed on separate origins in production
    # (Vercel + Render), so this needs real CORS with credentials, and the
    # session cookie needs SameSite=None + Secure to survive a cross-site
    # request. Locally (Vite dev server on a different port, but still
    # effectively same-site) SameSite=Lax over http works fine and is
    # simpler, so this defaults to "production" only via env var.
    is_production: bool = False

    @property
    def allowed_emails_list(self) -> list[str]:
        return [e.strip().lower() for e in self.allowed_emails.split(",") if e.strip()]

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [self.frontend_url] if self.frontend_url else []


settings = Settings()
