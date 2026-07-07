from app.auth.session import create_session_token, read_session_token


def test_valid_token_round_trips_the_email():
    token = create_session_token("lise@example.com")
    assert read_session_token(token) == "lise@example.com"


def test_tampered_token_is_rejected():
    token = create_session_token("lise@example.com")
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    assert read_session_token(tampered) is None


def test_garbage_token_is_rejected():
    assert read_session_token("not-a-real-token") is None
