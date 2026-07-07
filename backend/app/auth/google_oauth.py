"""Google OAuth (authorization-code flow) via Authlib. Deliberately not a
hosted auth provider (Auth0/Clerk) -- this app has 2 users and Authlib is
free and lightweight enough for that scale (see docs/domain-notes.md).
"""

from authlib.integrations.starlette_client import OAuth

from app.config import settings

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
