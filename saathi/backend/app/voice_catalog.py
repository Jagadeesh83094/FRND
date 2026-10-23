"""Voice catalog and character -> voice mapping.

Ground rules (from docs.sarvam.ai, verified):
  * `bulbul:v4-flash` speaker IDs follow `voice_language_style`, e.g.
    `kavitha_te_conversation`, `aparna_hi_customer`, `sunny_en_social`.
    v3 short names (`shubh`, `priya`, ...) are REJECTED on v4.
  * v4 Flash personas exist for: hi, en, enhi, bn, gu, kn, mr, pa, ta, te.
    There are NO `ml` / `od` personas -- those languages must use `bulbul:v3`.
  * The roster changes without notice; an unknown speaker returns HTTP 400 with
    the live list. We therefore validate every speaker against this catalog and
    fall back safely rather than trusting a name blindly.

Only IDs confirmed in the official docs are listed. Never invent one.
"""
from __future__ import annotations

V4 = "bulbul:v4-flash"
V3 = "bulbul:v3"

# Languages v4 Flash personas cover. Everything else falls back to v3.
V4_LANGUAGES = {"en-IN", "hi-IN", "bn-IN", "gu-IN", "kn-IN", "mr-IN", "pa-IN", "ta-IN", "te-IN"}
V3_LANGUAGES = {
    "hi-IN", "bn-IN", "ta-IN", "te-IN", "gu-IN", "kn-IN", "ml-IN",
    "mr-IN", "pa-IN", "od-IN", "en-IN",
}

# --- Curated, confirmed v4 Flash personas ---------------------------------- #
V4_VOICES = {
    # English (Indian accent)
    "sunny_en_social": {"speaker": "Sunny", "language": "en-IN", "style": "social, energetic"},
    "simran_en_customer": {"speaker": "Simran", "language": "en-IN", "style": "friendly"},
    "simran_en_sales": {"speaker": "Simran", "language": "en-IN", "style": "lively"},
    "aparna_en_companion": {"speaker": "Aparna", "language": "en-IN", "style": "warm companion"},
    "dev_en_conversational": {"speaker": "Dev", "language": "en-IN", "style": "conversational"},
    "dev_en_recovery": {"speaker": "Dev", "language": "en-IN", "style": "steady"},
    "neha_en_latenight": {"speaker": "Neha", "language": "en-IN", "style": "gentle, soft"},
    "neha_en_customer": {"speaker": "Neha", "language": "en-IN", "style": "calm"},
    "rohan_en_recovery": {"speaker": "Rohan", "language": "en-IN", "style": "measured"},
    "shubh_en_recovery": {"speaker": "Shubh", "language": "en-IN", "style": "calm, steady"},
    # Hindi
    "sunny_hi_reels": {"speaker": "Sunny", "language": "hi-IN", "style": "casual, fun"},
    "roopa_hi_companion": {"speaker": "Roopa", "language": "hi-IN", "style": "warm companion"},
    "shalini_hi_companion": {"speaker": "Shalini", "language": "hi-IN", "style": "affectionate"},
    "ratan_hi_customer_expressive": {"speaker": "Ratan", "language": "hi-IN", "style": "expressive"},
    "ratan_hi_documentary": {"speaker": "Ratan", "language": "hi-IN", "style": "reflective"},
    "ratan_hi_latenight_warm": {"speaker": "Ratan", "language": "hi-IN", "style": "warm, low-key"},
    "kavya_hi_conversational": {"speaker": "Kavya", "language": "hi-IN", "style": "conversational"},
    "ritu_hi_customer_warm": {"speaker": "Ritu", "language": "hi-IN", "style": "warm"},
    "mani_hi_conversational": {"speaker": "Mani", "language": "hi-IN", "style": "calm, clear"},
    "shubh_hi_customer": {"speaker": "Shubh", "language": "hi-IN", "style": "neutral"},
    "aditya_hi_conversational": {"speaker": "Aditya", "language": "hi-IN", "style": "conversational"},
    "ishita_hi_ads_informal": {"speaker": "Ishita", "language": "hi-IN", "style": "informal"},
    "roopa_hi_narration": {"speaker": "Roopa", "language": "hi-IN", "style": "storytelling"},
    # English-Hindi code-mixed
    "shubh_enhi_ads": {"speaker": "Shubh", "language": "hi-IN", "style": "code-mixed default"},
    "simran_enhi_customer": {"speaker": "Simran", "language": "hi-IN", "style": "code-mixed"},
    # Telugu
    "kavitha_te_conversation": {"speaker": "Kavitha", "language": "te-IN", "style": "conversation"},
    "kavitha_te_narration": {"speaker": "Kavitha", "language": "te-IN", "style": "narration"},
    "pooja_te_conversation": {"speaker": "Pooja", "language": "te-IN", "style": "conversation"},
    "tarun_te_narration": {"speaker": "Tarun", "language": "te-IN", "style": "narration"},
    # Other v4 languages
    "roopa_bn_conversational": {"speaker": "Roopa", "language": "bn-IN", "style": "conversational"},
    "arnab_bn_conversation": {"speaker": "Arnab", "language": "bn-IN", "style": "conversation"},
    "ishita_mr_conversational": {"speaker": "Ishita", "language": "mr-IN", "style": "conversational"},
    "chaitra_kn_conversation": {"speaker": "Chaitra", "language": "kn-IN", "style": "conversation"},
    "bhavik_gu_conversation": {"speaker": "Bhavik", "language": "gu-IN", "style": "conversation"},
    "anand_pa_conversation": {"speaker": "Anand", "language": "pa-IN", "style": "conversation"},
    "gokul_ta_narration": {"speaker": "Gokul", "language": "ta-IN", "style": "narration"},
    "aravind_ta_ads": {"speaker": "Aravind", "language": "ta-IN", "style": "expressive"},
}

# --- Bulbul v3 named speakers (all 11 languages, incl. ml-IN / od-IN) ------- #
V3_SPEAKERS = [
    "shubh", "aditya", "ritu", "priya", "neha", "rahul", "pooja", "rohan",
    "simran", "kavya", "amit", "dev", "ishita", "shreya", "ratan", "varun",
    "manan", "sumit", "roopa", "kabir", "aayan", "ashutosh", "advait", "anand",
    "tanya", "tarun", "sunny", "mani", "gokul", "vijay", "shruti", "suhani",
    "mohit", "kavitha", "rehan", "soham", "rupali",
]

# Recommended v3 short-name fallback per language (docs "Recommended Speakers").
V3_FALLBACK_BY_LANGUAGE = {
    "en-IN": "ratan", "hi-IN": "shubh", "te-IN": "ratan", "kn-IN": "shubh",
    "bn-IN": "rehan", "ta-IN": "ratan", "od-IN": "shubh", "ml-IN": "shubh",
    "mr-IN": "ratan", "pa-IN": "mani", "gu-IN": "ratan",
}


def is_v4_speaker(speaker_id: str) -> bool:
    return speaker_id in V4_VOICES


def is_v3_speaker(speaker_id: str) -> bool:
    return speaker_id.lower() in V3_SPEAKERS


def speaker_language(speaker_id: str) -> str | None:
    info = V4_VOICES.get(speaker_id)
    return info["language"] if info else None


def v3_fallback_for(language_code: str) -> tuple[str, str]:
    """Return (model, speaker) for a language that has no v4 persona."""
    return V3, V3_FALLBACK_BY_LANGUAGE.get(language_code, "shubh")


# --- Character -> per-language voice mapping ------------------------------- #
# Each character keeps a *voice identity* separate from its prompt (requirement E).
# primary_language is the character's default; the map covers its alternates.
CHARACTER_VOICES: dict[str, dict] = {
    "best_friend": {
        "primary_language": "en-IN",
        "map": {"en-IN": "sunny_en_social", "hi-IN": "sunny_hi_reels", "te-IN": "kavitha_te_conversation"},
        "pace": 1.05,
    },
    "mom": {
        "primary_language": "en-IN",
        "map": {"en-IN": "aparna_en_companion", "hi-IN": "roopa_hi_companion", "te-IN": "pooja_te_conversation"},
        "pace": 0.95,
    },
    "dad": {
        "primary_language": "en-IN",
        "map": {"en-IN": "dev_en_conversational", "hi-IN": "ratan_hi_customer_expressive", "te-IN": "tarun_te_narration"},
        "pace": 0.98,
    },
    "grandmother": {
        "primary_language": "hi-IN",
        "map": {"en-IN": "neha_en_latenight", "hi-IN": "shalini_hi_companion", "te-IN": "kavitha_te_narration"},
        "pace": 0.9,
    },
    "grandfather": {
        "primary_language": "hi-IN",
        "map": {"en-IN": "shubh_en_recovery", "hi-IN": "ratan_hi_documentary", "te-IN": "tarun_te_narration"},
        "pace": 0.9,
    },
    "sibling": {
        "primary_language": "en-IN",
        "map": {"en-IN": "simran_en_customer", "hi-IN": "kavya_hi_conversational", "te-IN": "pooja_te_conversation"},
        "pace": 1.05,
    },
    "mentor": {
        "primary_language": "en-IN",
        "map": {"en-IN": "rohan_en_recovery", "hi-IN": "mani_hi_conversational", "te-IN": "tarun_te_narration"},
        "pace": 0.95,
    },
    "custom": {
        "primary_language": "en-IN",
        "map": {"en-IN": "shubh_enhi_ads", "hi-IN": "shubh_hi_customer", "te-IN": "kavitha_te_conversation"},
        "pace": 1.0,
    },
}


def resolve_voice(character_id: str, language_code: str) -> dict:
    """Resolve (model, speaker, pace) for a character + language.

    Never returns an unsupported speaker: falls back to the character's primary
    language persona, then to a v3 short name, and reports which fallback fired
    so the API can tell the user (requirement E).
    """
    entry = CHARACTER_VOICES.get(character_id, CHARACTER_VOICES["custom"])
    requested = language_code

    def pick(lang: str) -> str | None:
        sid = entry["map"].get(lang)
        if sid and is_v4_speaker(sid):
            return sid
        return None

    # 1. Exact language, when a v4 persona exists and the language is v4-capable.
    if language_code in V4_LANGUAGES:
        sid = pick(language_code)
        if sid:
            return {"model": V4, "speaker_id": sid, "language_code": language_code,
                    "pace": entry["pace"], "fallback": None}

    # 2. Malayalam / Odia (and any non-v4 language) -> v3 short name.
    if language_code in V3_LANGUAGES and language_code not in V4_LANGUAGES:
        model, speaker = v3_fallback_for(language_code)
        return {"model": model, "speaker_id": speaker, "language_code": language_code,
                "pace": entry["pace"],
                "fallback": {"reason": "language_has_no_v4_persona", "requested_language": requested}}

    # 3. Unsupported language entirely -> character's primary language persona.
    primary = entry["primary_language"]
    sid = pick(primary)
    if sid:
        return {"model": V4, "speaker_id": sid, "language_code": primary,
                "pace": entry["pace"],
                "fallback": {"reason": "language_unsupported", "requested_language": requested}}

    # 4. Last resort: v3 short name for the primary language.
    model, speaker = v3_fallback_for(primary)
    return {"model": model, "speaker_id": speaker, "language_code": primary,
            "pace": entry["pace"],
            "fallback": {"reason": "no_persona_available", "requested_language": requested}}
