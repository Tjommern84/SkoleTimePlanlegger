"""Signed, stateless session cookie -- appropriate for a 2-user app (see
docs/domain-notes.md): no session store/DB table needed, just a signed
token holding the user's email, verified on every request.
"""

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

SESSION_COOKIE_NAME = "session"
_MAX_AGE_SECONDS = 60 * 60 * 24 * 30  # 30 days

_serializer = URLSafeTimedSerializer(settings.session_secret, salt="timetable-session")


def create_session_token(email: str) -> str:
    return _serializer.dumps({"email": email})


def read_session_token(token: str) -> str | None:
    """Returns the email encoded in a valid, unexpired token, or None."""
    try:
        data = _serializer.loads(token, max_age=_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    return data.get("email")
