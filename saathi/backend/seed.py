"""Seed the built-in character library and a demo user.

Safe to run repeatedly: definitions are updated in place and user customisations
are preserved.
"""
from __future__ import annotations

from app.db import Base, SessionLocal, engine
from app.services import character_service


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        character_service.ensure_builtin_definitions(db)
        user = character_service.get_or_create_user(db, "demo@saathi.app", "Demo User")
        for ch in character_service.list_user_characters(db, user):
            print(f"  {ch['id']:<14} {ch['display_name']:<16} voice={ch['voice']['speaker_id']} ({ch['voice']['language_code']})")
        print(f"\nSeeded {len(character_service.list_user_characters(db, user))} characters for {user.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
