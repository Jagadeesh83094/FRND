"""Shared pytest fixtures.

Sets a throwaway database and forces the offline mock provider BEFORE importing
the app, so tests never touch the network or a real API key.
"""
from __future__ import annotations

import os
import tempfile

import pytest

_TMP = tempfile.mkdtemp(prefix="saathi_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["PROVIDER_MODE"] = "mock"
os.environ["SARVAM_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:  # triggers lifespan -> seeds built-in library
        yield c


@pytest.fixture()
def user_headers():
    return {"X-User-Email": "tester@saathi.app"}


@pytest.fixture()
def second_user_headers():
    return {"X-User-Email": "other@saathi.app"}
