from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app import models  # register model tables on Base before creating the test schema


@pytest.fixture()
def isolated_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def test_production_rejects_development_identity(monkeypatch, isolated_db):
    from app.routers.deps import get_current_user
    monkeypatch.setattr("app.routers.deps.get_settings", lambda: type("S", (), {"environment": "production"})())
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization=None, x_user_email="victim@example.com", db=isolated_db)
    assert exc.value.status_code == 401


def test_development_rejects_invalid_email(monkeypatch, isolated_db):
    from app.routers.deps import get_current_user
    monkeypatch.setattr("app.routers.deps.get_settings", lambda: type("S", (), {"environment": "development"})())
    with pytest.raises(HTTPException) as exc:
        get_current_user(authorization=None, x_user_email="not-an-email", db=isolated_db)
    assert exc.value.status_code == 400


def test_rate_limiter_rejects_excess_requests():
    from starlette.requests import Request
    from app.rate_limit import enforce_rate_limit, _EVENTS, _LOCK

    with _LOCK:
        _EVENTS.clear()
    request = Request({"type": "http", "client": ("127.0.0.1", 12345)})
    enforce_rate_limit(request, bucket="test", limit=1, window_seconds=60)
    with pytest.raises(HTTPException) as exc:
        enforce_rate_limit(request, bucket="test", limit=1, window_seconds=60)
    assert exc.value.status_code == 429



def test_password_hash_and_token_signature():
    from app.auth_service import hash_password, verify_password, issue_access_token, verify_access_token

    hashed = hash_password("a-strong-test-password")
    assert hashed != "a-strong-test-password"
    assert verify_password("a-strong-test-password", hashed)
    assert not verify_password("wrong-password", hashed)

    token = issue_access_token(42, "test-signing-key-with-at-least-32-chars")
    assert verify_access_token(token, "test-signing-key-with-at-least-32-chars") == 42
    with pytest.raises(HTTPException) as exc:
        verify_access_token(token, "different-signing-key-with-32-chars")
    assert exc.value.status_code == 401


def test_password_verifier_rejects_unsafe_iteration_count():
    from app.auth_service import verify_password

    # An attacker who can corrupt a stored credential must not force a huge
    # PBKDF2 workload during login.
    assert not verify_password("password", "pbkdf2_sha256$999999999$YWJj$YWJj")
    assert not verify_password("password", "pbkdf2_sha256$600000$YWJj$YWJj")


def test_access_token_rejects_wrong_secret_and_malformed_payload():
    import base64
    import json
    import time
    from app.auth_service import verify_access_token

    secret = "test-signing-key-with-at-least-32-chars"
    payload = base64.urlsafe_b64encode(json.dumps({
        "sub": "42", "iat": int(time.time()), "exp": int(time.time()) + 60 * 60 * 24 * 365
    }).encode()).rstrip(b"=").decode()
    import hashlib, hmac
    signing_input = f"saathi-v1.{payload}".encode()
    signature = base64.urlsafe_b64encode(hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()).rstrip(b"=").decode()
    with pytest.raises(HTTPException) as exc:
        verify_access_token(f"saathi-v1.{payload}.{signature}", secret)
    assert exc.value.status_code == 401
