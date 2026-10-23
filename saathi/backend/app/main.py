"""Saathi FastAPI application."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import Base, SessionLocal, engine
from .routers import auth, characters, chat, conversations, memories, onboarding, voice
from .services import character_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: ensure tables exist and the built-in library is seeded.
    # Production uses `alembic upgrade head` (see README); create_all is a no-op
    # on an already-migrated database.
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        character_service.ensure_builtin_definitions(db)
    finally:
        db.close()
    yield


settings = get_settings()
app = FastAPI(title="Saathi API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, characters, chat, conversations, memories, voice, onboarding):
    app.include_router(module.router)


@app.get("/api/health")
def health():
    from .providers import get_provider
    provider = get_provider()
    return {
        "status": "ok",
        "provider": provider.name,
        "live": provider.is_live,
        "environment": settings.environment,
    }
