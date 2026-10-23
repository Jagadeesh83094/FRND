"""Character library management: definitions, user instances, customisation."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..characters import CHARACTER_LIBRARY, BUILTIN_BY_ID
from ..models import CharacterDefinition, CharacterPreference, User, UserCharacter, VoiceConfiguration
from ..safety import CustomCharacterError, validate_custom_character
from ..voice_catalog import V4, resolve_voice

AI_DISCLOSURE = (
    "Every character in Saathi is an AI-generated companion. They are fictional "
    "and inspired by broad conversational styles -- they are not your real family, "
    "friends, or any real person, and they have no genuine memories. They can offer "
    "company and a place to think, but they are not a substitute for the people in "
    "your life or for professional care."
)


# --------------------------------------------------------------------------- #
# Voice configuration helpers
# --------------------------------------------------------------------------- #
def ensure_voice_config(
    db: Session,
    *,
    provider: str,
    model: str,
    speaker_id: str,
    language_code: str,
    pace: float = 1.0,
    fallback_speaker: str | None = None,
    is_default: bool = False,
) -> VoiceConfiguration:
    existing = db.scalar(
        select(VoiceConfiguration).where(
            VoiceConfiguration.provider == provider,
            VoiceConfiguration.model == model,
            VoiceConfiguration.speaker_id == speaker_id,
            VoiceConfiguration.language_code == language_code,
        )
    )
    if existing:
        return existing
    vc = VoiceConfiguration(
        provider=provider, model=model, speaker_id=speaker_id,
        language_code=language_code, pace=pace,
        fallback_speaker=fallback_speaker, is_default=is_default,
    )
    db.add(vc)
    db.flush()
    return vc


def _definition_voice(db: Session, definition: CharacterDefinition) -> VoiceConfiguration:
    resolved = resolve_voice(definition.id, _primary_language(definition))
    vc = ensure_voice_config(
        db,
        provider="sarvam",
        model=resolved["model"],
        speaker_id=resolved["speaker_id"],
        language_code=resolved["language_code"],
        pace=resolved["pace"],
        is_default=True,
    )
    if definition.default_voice_config_id != vc.id:
        definition.default_voice_config_id = vc.id
        db.flush()
    return vc


def _primary_language(definition: CharacterDefinition) -> str:
    langs = definition.languages or ["en-IN"]
    return langs[0]


# --------------------------------------------------------------------------- #
# Built-in definitions (idempotent seed; never clobbers user customisations)
# --------------------------------------------------------------------------- #
def ensure_builtin_definitions(db: Session) -> None:
    for spec in CHARACTER_LIBRARY:
        definition = db.get(CharacterDefinition, spec["id"])
        if definition is None:
            definition = CharacterDefinition(id=spec["id"], kind="builtin")
            db.add(definition)
        # Update content fields; bump version only when something changed.
        changed = False
        for field in (
            "display_name", "default_nickname", "name_variants", "avatar_ref",
            "short_description", "personality_description", "conversational_style",
            "tone", "languages", "example_greeting", "response_length",
            "behaviors", "do_list", "dont_list",
        ):
            new_val = spec.get(field)
            if getattr(definition, field, None) != new_val:
                setattr(definition, field, new_val)
                changed = True
        if changed and definition.id is not None:
            definition.version = (definition.version or 1) + 1
        definition.is_active = True
        db.flush()
        _definition_voice(db, definition)
    db.commit()


# --------------------------------------------------------------------------- #
# Users (lightweight auth stub for local dev)
# --------------------------------------------------------------------------- #
def get_or_create_user(db: Session, email: str, display_name: str | None = None) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, display_name=display_name or email.split("@")[0])
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# --------------------------------------------------------------------------- #
# User characters
# --------------------------------------------------------------------------- #
def list_definitions(db: Session) -> list[CharacterDefinition]:
    return list(db.scalars(select(CharacterDefinition).where(CharacterDefinition.is_active.is_(True))
                           .order_by(CharacterDefinition.id)))


def get_or_create_user_character(
    db: Session, user: User, definition_id: str
) -> UserCharacter:
    definition = db.get(CharacterDefinition, definition_id)
    if definition is None or not definition.is_active:
        raise ValueError(f"Unknown character: {definition_id}")

    uc = db.scalar(
        select(UserCharacter).where(
            UserCharacter.user_id == user.id,
            UserCharacter.character_definition_id == definition_id,
        )
    )
    if uc:
        return uc

    # Ensure the definition has a default voice row, but do NOT pin it on the
    # user instance: leaving voice_config_id NULL lets the voice resolve
    # dynamically per selected language. It is only pinned when the user
    # explicitly chooses a specific voice.
    _definition_voice(db, definition)
    uc = UserCharacter(
        user_id=user.id,
        character_definition_id=definition_id,
        is_custom=(definition.kind == "custom"),
        display_name=definition.default_nickname or definition.display_name,
        nickname=definition.default_nickname,
        language_prefs=list(definition.languages or ["en-IN"])[:1] or ["en-IN"],
        response_length=definition.response_length,
        voice_config_id=None,
    )
    db.add(uc)
    db.commit()
    db.refresh(uc)
    return uc


def _effective_voice(db: Session, definition: CharacterDefinition, uc: UserCharacter) -> dict:
    """Resolve the voice actually used, honouring a user override."""
    if uc.voice_config_id:
        vc = db.get(VoiceConfiguration, uc.voice_config_id)
        if vc:
            return {
                "provider": vc.provider, "model": vc.model, "speaker_id": vc.speaker_id,
                "language_code": vc.language_code, "pace": vc.pace,
                "fallback_speaker": vc.fallback_speaker, "config_version": vc.config_version,
                "is_fallback": False, "fallback_reason": None,
            }
    lang = (uc.language_prefs or [_primary_language(definition)])[0]
    resolved = resolve_voice(definition.id, lang)
    return {
        "provider": "sarvam", "model": resolved["model"], "speaker_id": resolved["speaker_id"],
        "language_code": resolved["language_code"], "pace": resolved["pace"],
        "fallback_speaker": None, "config_version": 1,
        "is_fallback": resolved["fallback"] is not None,
        "fallback_reason": (resolved["fallback"] or {}).get("reason"),
    }


def character_to_dict(db: Session, definition: CharacterDefinition, uc: UserCharacter) -> dict:
    """Merged view for the API and the prompt builder."""
    overrides = uc.personality_overrides or {}
    return {
        "id": definition.id,
        "definition_id": definition.id,
        "user_character_id": uc.id,
        "is_custom": uc.is_custom,
        "display_name": uc.display_name or definition.display_name,
        "nickname": uc.nickname,
        "name_variants": definition.name_variants or {},
        "avatar_ref": definition.avatar_ref,
        "short_description": definition.short_description,
        "personality_description": overrides.get("personality") or definition.personality_description,
        "conversational_style": overrides.get("conversational_style") or definition.conversational_style,
        "languages": definition.languages or [],
        "language_prefs": uc.language_prefs or [],
        "example_greeting": definition.example_greeting,
        "response_length": uc.response_length or definition.response_length,
        "behaviors": definition.behaviors or [],
        "voice": _effective_voice(db, definition, uc),
        "customized": bool(uc.nickname or overrides or uc.display_name != definition.display_name),
        "_definition": definition,
        "_uc": uc,
    }


def list_user_characters(db: Session, user: User) -> list[dict]:
    out: list[dict] = []
    for definition in list_definitions(db):
        uc = db.scalar(
            select(UserCharacter).where(
                UserCharacter.user_id == user.id,
                UserCharacter.character_definition_id == definition.id,
            )
        )
        if uc is None:
            uc = get_or_create_user_character(db, user, definition.id)
        out.append(character_to_dict(db, definition, uc))
    return out


def update_user_character(
    db: Session, user: User, uc: UserCharacter, payload: dict
) -> UserCharacter:
    definition = db.get(CharacterDefinition, uc.character_definition_id) if uc.character_definition_id else None

    if payload.get("display_name") is not None:
        uc.display_name = payload["display_name"].strip()[:40] or uc.display_name
    if payload.get("nickname") is not None:
        uc.nickname = payload["nickname"].strip()[:40] or None
    if payload.get("language_prefs"):
        uc.language_prefs = [l for l in payload["language_prefs"] if isinstance(l, str)][:3]
    if payload.get("response_length"):
        uc.response_length = payload["response_length"]

    overrides = payload.get("personality_overrides")
    if overrides:
        # Validate any custom personality text against the safety rules.
        safe = validate_custom_character({
            "display_name": uc.display_name,
            "personality": overrides.get("personality", ""),
            "conversational_style": overrides.get("conversational_style", ""),
            "language": (uc.language_prefs or ["en-IN"])[0],
        })
        merged = dict(uc.personality_overrides or {})
        if "personality" in overrides:
            merged["personality"] = safe["personality"]
        if "conversational_style" in overrides:
            merged["conversational_style"] = safe["conversational_style"]
        uc.personality_overrides = merged

    # Voice override
    voice_id = payload.get("voice_id")
    voice_lang = payload.get("voice_language")
    if voice_id and definition is not None:
        from ..voice_catalog import V4_VOICES, V3_SPEAKERS, is_v4_speaker, is_v3_speaker
        model = V4 if is_v4_speaker(voice_id) else ("bulbul:v3" if is_v3_speaker(voice_id) else None)
        if model is None:
            raise ValueError(f"Unsupported voice id: {voice_id}")
        lang = voice_lang or (V4_VOICES.get(voice_id, {}) or {}).get("language") or _primary_language(definition)
        vc = ensure_voice_config(
            db, provider="sarvam", model=model, speaker_id=voice_id,
            language_code=lang, pace=1.0, is_default=False,
        )
        uc.voice_config_id = vc.id

    db.commit()
    db.refresh(uc)
    return uc


def create_custom_character(db: Session, user: User, payload: dict) -> dict:
    try:
        clean = validate_custom_character(payload)
    except CustomCharacterError:
        raise

    # Store the custom definition under a unique slug.
    base = "custom"
    n = 1
    slug = f"{base}_{user.id}_{n}"
    while db.get(CharacterDefinition, slug) is not None:
        n += 1
        slug = f"{base}_{user.id}_{n}"

    tone = clean["tone"] or BUILTIN_BY_ID["custom"]["tone"]
    definition = CharacterDefinition(
        id=slug,
        kind="custom",
        display_name=clean["display_name"],
        default_nickname=clean["nickname"],
        name_variants={},
        avatar_ref="custom",
        short_description=(clean["personality"][:180] or "A custom companion."),
        personality_description=clean["personality"] or "A custom companion the user defined.",
        conversational_style=clean["conversational_style"] or "Defined by the user.",
        tone=tone,
        languages=[clean["language"]],
        example_greeting="Hi, I'm here. What would you like to talk about?",
        response_length=clean["response_length"],
        behaviors=["Follow the user's chosen persona while staying safe and honest."],
        do_list=["Stay in the user's chosen character within safe bounds."],
        dont_list=["Never adopt a persona that claims to be a real person."],
    )
    db.add(definition)
    db.flush()
    _definition_voice(db, definition)

    uc = get_or_create_user_character(db, user, slug)
    if clean.get("voice_id"):
        update_user_character(db, user, uc, {"voice_id": clean["voice_id"], "voice_language": clean["language"]})
    return character_to_dict(db, definition, uc)
