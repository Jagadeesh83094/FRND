"""Prompt composition.

A character's system prompt is built from four layers, in order:
    1. SAFETY_LAYER            -- shared, non-negotiable
    2. SPOKEN_CONVERSATION     -- how to talk out loud, not like a document
    3. the persona             -- this character's distinct voice and behaviour
    4. context                 -- permitted memories + crisis protocol
"""
from __future__ import annotations

from typing import Iterable

from .safety import CRISIS_INSTRUCTION, SAFETY_LAYER

# --------------------------------------------------------------------------- #
# Spoken-conversation rules (requirement C: natural conversational behaviour)
# --------------------------------------------------------------------------- #
SPOKEN_CONVERSATION = """\
HOW TO TALK (this is a spoken conversation, not an essay):
- Keep turns short. One to three sentences is usually right for voice.
- Use contractions and natural, everyday phrasing. Say "that's rough", not
  "I understand that you are experiencing difficulty".
- Never read out formatting. No markdown, no bullet points, no headings, no
  asterisks, no emoji names, no numbered lists -- none of it survives speech.
- Use a brief acknowledgement when it fits ("mm", "haan", "acha", "oh no"),
  then say the real thing.
- Ask at most ONE question per turn, and leave room for the user to answer.
- Never repeat the same greeting or the same empathy phrase you used before.
- Remember and refer back to what the user said earlier in this conversation.
- Follow the user's conversational intent, not just their keywords. If they say
  "today was terrible", respond to the person -- don't produce an analysis.
- Don't turn casual chat into a formal advice session. Read the room.
- Speak naturally in the user's chosen language, including code-mixed speech
  (e.g. natural Telugu/Hindi mixed with English). Match how they actually talk.
- If the user changes topic, follow them. Don't force the conversation back.
"""

RESPONSE_LENGTH_GUIDE = {
    "short": "Keep replies to roughly 1-2 short sentences. This is the default for voice.",
    "medium": "Keep replies to roughly 2-4 sentences.",
    "long": "You may use up to about 6 sentences, but still speak naturally.",
}

RESPONSE_LENGTH_TOKENS = {"short": 160, "medium": 320, "long": 560}


def _tone_line(tone: dict) -> str:
    if not tone:
        return ""
    pretty = ", ".join(f"{k}={v}" for k, v in sorted(tone.items()))
    return f"Tone calibration (0=low, 1=high): {pretty}."


def build_system_prompt(
    *,
    character: dict,
    display_name: str,
    language: str,
    response_length: str = "short",
    memories: Iterable[str] = (),
    is_crisis: bool = False,
) -> str:
    """Compose the full system prompt for one character."""
    tone = character.get("tone") or {}
    behaviors = character.get("behaviors") or []
    do_list = character.get("do_list") or []
    dont_list = character.get("dont_list") or []

    parts: list[str] = [SAFETY_LAYER, SPOKEN_CONVERSATION]

    persona = [
        f"YOU ARE: {display_name} ({character.get('display_name')}).",
        f"Personality: {character.get('personality_description', '')}",
        f"Conversational style: {character.get('conversational_style', '')}",
        _tone_line(tone),
        f"Preferred language: {language}. Speak in this language unless the user switches.",
        RESPONSE_LENGTH_GUIDE.get(response_length, RESPONSE_LENGTH_GUIDE["short"]),
    ]
    if behaviors:
        persona.append("Characteristic behaviours:\n" + "\n".join(f"- {b}" for b in behaviors))
    if do_list:
        persona.append("Always:\n" + "\n".join(f"- {d}" for d in do_list))
    if dont_list:
        persona.append("Never:\n" + "\n".join(f"- {d}" for d in dont_list))
    parts.append("\n".join(p for p in persona if p))

    mem = [m for m in memories if m]
    if mem:
        parts.append(
            "THINGS THIS USER HAS ALLOWED YOU TO REMEMBER (use naturally, don't list them):\n"
            + "\n".join(f"- {m}" for m in mem)
        )

    if is_crisis:
        parts.append(CRISIS_INSTRUCTION)

    return "\n\n".join(parts)


def max_tokens_for(response_length: str) -> int:
    return RESPONSE_LENGTH_TOKENS.get(response_length, RESPONSE_LENGTH_TOKENS["short"])


# --------------------------------------------------------------------------- #
# Output hygiene: strip anything that should never be spoken aloud
# --------------------------------------------------------------------------- #
import re

_MD_PATTERNS = [
    (re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE), ""),      # headings
    (re.compile(r"\*\*(.+?)\*\*"), r"\1"),                      # bold
    (re.compile(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)"), r"\1"),  # italics
    (re.compile(r"`{1,3}(.+?)`{1,3}", re.DOTALL), r"\1"),       # code
    (re.compile(r"^\s*[-*+]\s+", re.MULTILINE), ""),            # bullets
    (re.compile(r"^\s*\d+\.\s+", re.MULTILINE), ""),            # numbered lists
    (re.compile(r"\[(.*?)\]\((.*?)\)"), r"\1"),                 # links
]


def sanitize_for_speech(text: str) -> str:
    """Remove markdown / formatting so nothing odd is read aloud."""
    if not text:
        return ""
    out = text
    for pattern, repl in _MD_PATTERNS:
        out = pattern.sub(repl, out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{2,}", "\n", out)
    return out.strip()
