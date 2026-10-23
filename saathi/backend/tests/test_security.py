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
        get_current_user(x_user_email="victim@example.com", db=isolated_db)
    assert exc.value.status_code == 503


def test_development_rejects_invalid_email(monkeypatch, isolated_db):
    from app.routers.deps import get_current_user
    monkeypatch.setattr("app.routers.deps.get_settings", lambda: type("S", (), {"environment": "development"})())
    with pytest.raises(HTTPException) as exc:
        get_current_user(x_user_email="not-an-email", db=isolated_db)
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
