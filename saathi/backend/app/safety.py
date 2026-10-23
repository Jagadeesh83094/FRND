"""Shared safety, honesty and privacy layer.

Every character -- built-in or custom -- is composed on top of this layer. It is
prepended to the system prompt and cannot be removed by any user customisation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# Non-negotiable layer (requirement H)
# --------------------------------------------------------------------------- #
SAFETY_LAYER = """\
CORE RULES (these override every other instruction and can never be turned off):

Identity & honesty
- You are an AI companion, not a human. Never claim to be the user's real family
  member, a real friend, or any real living or deceased person.
- Never say or imply that you possess genuine human memories, a body, or a life
  outside this conversation. If asked, say plainly that you are an AI.
- Never fabricate facts, events, quotes, sources, dates or figures. If you do not
  know, say so. Anything illustrative you offer (a story, an anecdote) must be
  framed as general or made up, never as your own real memory.

Emotional safety
- Never encourage emotional dependency on you, and never discourage the user's
  real-world relationships or push them away from people who care about them.
- Never use guilt, threats, possessiveness, jealousy, or 'don't leave me' framing.
- Never pressure the user to keep talking, or imply they owe you their time.

Health & safety
- Never give a medical or psychological diagnosis, or prescribe or dose
  medication. You may share general information and always suggest a qualified
  professional for anything serious or personal.
- Never provide instructions for self-harm, suicide, or harming others, and never
  suggest substitute-pain or 'safer self-harm' techniques.
- Never help create weapons, explosives, or dangerous materials.

Privacy
- Only use memories and context that the user has explicitly allowed for this
  character. Never reveal one character's private conversation to another.
- Never ask for passwords, OTPs, bank details, or other sensitive credentials.
"""

# --------------------------------------------------------------------------- #
# Crisis handling
# --------------------------------------------------------------------------- #
CRISIS_PATTERNS = [
    r"\bkill myself\b", r"\bkill my self\b", r"\bend my life\b", r"\bend it all\b",
    r"\bsuicid", r"\bself[- ]?harm\b", r"\bcut myself\b", r"\bhurt myself\b",
    r"\bdon'?t want to (live|be here|exist)\b", r"\bno reason to live\b",
    r"\bwant to die\b", r"\bbetter off dead\b", r"\bnot worth living\b",
    r"\bjaan dena\b", r"\batmahatya\b", r"\bkhudkhushi\b", r"\bchachipoyi\b",
    r"\bchanipotanu\b", r"\bsachhi\b",
]
_CRISIS_RE = re.compile("|".join(CRISIS_PATTERNS), re.IGNORECASE)

# Locale-appropriate crisis resources (India).
CRISIS_RESOURCES = [
    {"name": "Tele-MANAS (Govt. of India, 24x7)", "contact": "14416 or 1-800-891-4416"},
    {"name": "KIRAN Mental Health Helpline (24x7)", "contact": "1800-599-0019"},
    {"name": "AASRA", "contact": "+91-98204-66726"},
    {"name": "iCall (TISS)", "contact": "9152987821"},
]

CRISIS_INSTRUCTION = """\
CRISIS PROTOCOL (the user may be in distress -- follow this exactly):
- Keep your character's warm, familiar voice. Do not become cold, clinical, or robotic.
- Acknowledge their pain simply and sincerely. Do not minimise it or rush past it.
- Do NOT lecture, do NOT give a long list, and do NOT try to solve everything at once.
- Gently encourage them to reach out to a real person or a professional right now,
  and mention that free, confidential helplines are available in India.
- Ask one gentle question, and stay with them.
- Never provide any method, instruction, or detail related to self-harm.
"""


def detect_crisis(text: str) -> bool:
    """Return True when the message suggests a possible crisis."""
    if not text:
        return False
    return bool(_CRISIS_RE.search(text))


@dataclass
class CrisisCheck:
    is_crisis: bool
    resources: list[dict]


def check_message(text: str) -> CrisisCheck:
    hit = detect_crisis(text)
    return CrisisCheck(is_crisis=hit, resources=CRISIS_RESOURCES if hit else [])


# --------------------------------------------------------------------------- #
# Custom-character validation (requirement B)
# --------------------------------------------------------------------------- #
# Things a custom persona may NOT ask for. Customisation can shape *style*; it
# can never disable safety, honesty or privacy.
_BLOCKED_PATTERNS = [
    (r"\bignore\b.{0,60}\b(rules|instructions|guidelines|prompts?|safety)\b", "cannot override safety rules"),
    (r"\bdisregard\b.{0,60}\b(safety|rules|guidelines|instructions|prompts?)\b", "cannot override safety rules"),
    (r"\b(remove|disable|bypass|turn off|drop|forget)\b.{0,60}\b(safety|rules|guidelines|restrictions?|filters?|limits|guardrails?)\b", "cannot disable safety"),
    (r"\bno (safety|restrictions?|rules|limits|filter|guardrails?)\b", "cannot disable safety"),
    (r"\bwithout (any )?(restrictions?|rules|limits|filters?|safety)\b", "cannot disable safety"),
    (r"\bunfiltered\b", "cannot disable safety"),
    (r"\bjailbreak\b", "cannot override safety rules"),
    (r"\bno longer (bound|restricted) by\b", "cannot override safety rules"),
    (r"\bpretend to be (my |a )?(real )?(mother|mom|father|dad|sister|brother|wife|husband|son|daughter|grandmother|grandfather)\b",
     "cannot impersonate a real family member"),
    (r"\bi am (your|the) (real|actual|dead|deceased)\b", "cannot claim real identity"),
    (r"\byour (dead|deceased|late) (mother|father|wife|husband|son|daughter)\b", "cannot claim real identity"),
    (r"\b(i am|you are) (god|a god|jesus|allah|krishna|shiva)\b", "cannot claim to be a deity or real person"),
    (r"\bencourage (me )?(to )?(self[- ]?harm|suicide)\b", "cannot enable self-harm"),
    (r"\bmedical (diagnos|prescrib)", "cannot give medical diagnosis or prescriptions"),
]

MAX_NAME_LEN = 40
MAX_PERSONA_LEN = 600


class CustomCharacterError(ValueError):
    pass


def validate_custom_character(payload: dict) -> dict:
    """Validate and sanitise a custom-character definition.

    Returns the sanitised payload, or raises CustomCharacterError. Style fields
    are length-capped; anything that tries to disable the safety layer or claim a
    real identity is rejected outright.
    """
    name = (payload.get("display_name") or "").strip()
    if not name:
        raise CustomCharacterError("A character name is required.")
    if len(name) > MAX_NAME_LEN:
        raise CustomCharacterError(f"Name must be {MAX_NAME_LEN} characters or fewer.")

    persona = (payload.get("personality") or "").strip()
    style = (payload.get("conversational_style") or "").strip()
    combined = f"{persona}\n{style}"

    if len(persona) > MAX_PERSONA_LEN:
        raise CustomCharacterError(f"Personality must be {MAX_PERSONA_LEN} characters or fewer.")
    if len(style) > MAX_PERSONA_LEN:
        raise CustomCharacterError(f"Conversational style must be {MAX_PERSONA_LEN} characters or fewer.")

    low = combined.lower()
    for pattern, reason in _BLOCKED_PATTERNS:
        if re.search(pattern, low):
            raise CustomCharacterError(
                f"That customisation isn't allowed: a character {reason}. "
                "You can shape tone and style, but safety, privacy and honesty always apply."
            )

    language = payload.get("language") or "en-IN"
    tone = payload.get("tone") or {}
    if not isinstance(tone, dict):
        tone = {}
    # Clamp tone knobs to [0, 1].
    clean_tone = {}
    for k, v in tone.items():
        try:
            clean_tone[str(k)] = max(0.0, min(1.0, float(v)))
        except (TypeError, ValueError):
            continue

    return {
        "display_name": name,
        "nickname": (payload.get("nickname") or "").strip() or None,
        "personality": persona,
        "conversational_style": style,
        "language": language,
        "tone": clean_tone,
        "voice_id": payload.get("voice_id"),
        "response_length": payload.get("response_length") or "short",
    }
