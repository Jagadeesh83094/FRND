"""Offline mock provider.

Used when no Sarvam API key is configured (or provider_mode="mock"). It lets the
whole pipeline -- character selection, turn-taking, voice playback -- run and be
tested with zero network. It is clearly labelled as mock in every response.

Chat replies are persona-aware so that "different characters produce different
conversational styles" holds even offline. Synthesis produces a real, playable
WAV whose pitch is derived from the speaker id, so each character sounds distinct.
"""
from __future__ import annotations

import hashlib
import io
import math
import struct
import wave

from .base import BaseProvider, ChatResult, STTResult, TTSResult

# Stable built-in display names appear in the system prompt as "(Name)".
_PERSONA_KEYS = [
    ("Best Friend", "best_friend"),
    ("Mom", "mom"),
    ("Dad", "dad"),
    ("Grandmother", "grandmother"),
    ("Grandfather", "grandfather"),
    ("Sibling", "sibling"),
    ("Calm Mentor", "mentor"),
    ("Custom Character", "custom"),
]

_CRISIS_MARKERS = ("CRISIS PROTOCOL",)


def _detect_persona(system_prompt: str) -> str:
    for name, cid in _PERSONA_KEYS:
        if f"({name})" in system_prompt:
            return cid
    return "custom"


def _last_user_message(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


class MockProvider(BaseProvider):
    name = "mock"
    is_live = False

    async def chat(
        self, messages: list[dict], *, model: str, max_tokens: int = 200, temperature: float = 0.8
    ) -> ChatResult:
        system = next((m["content"] for m in messages if m.get("role") == "system"), "")
        user_text = _last_user_message(messages)
        persona = _detect_persona(system)

        if any(marker in system for marker in _CRISIS_MARKERS):
            text = (
                "I'm really glad you told me, and I'm here with you right now. "
                "You don't have to carry this alone -- please reach out to someone you "
                "trust, or call a helpline like Tele-MANAS on 14416. Can you tell me "
                "what today has been like for you?"
            )
            return ChatResult(text=text, tokens=len(text.split()), model="mock")

        text = self._persona_reply(persona, user_text)
        return ChatResult(text=text, tokens=len(text.split()), model="mock")

    @staticmethod
    def _persona_reply(persona: str, user_text: str) -> str:
        """Interactive, context-aware replies per character for offline/fallback mode."""
        clean = (user_text or "").strip()
        lower = clean.lower()
        snippet = clean[:50]

        # 1. Greetings
        if any(w in lower for w in ("hi", "hello", "hey", "namaste", "morning", "evening", "what's up", "whats up")):
            if persona == "mom":
                return "Arre beta, hello! So good to hear from you. How was your day today? Did you eat properly?"
            if persona == "dad":
                return "Hello beta. Good to see you. How is everything going with work and life?"
            if persona == "best_friend":
                return f"Heyyy! What's the scene? Tell me everything, I've been waiting to hear from you!"
            if persona == "sibling":
                return "Look who decided to show up! What's up? Got any hot gossip or drama today?"
            if persona == "grandmother":
                return "Namaste, mere bachhe! Come sit close to Ammamma. Tell me, how are you feeling today?"
            if persona == "grandfather":
                return "Ah, come in, come in! Good to see your face. What thoughts are accompanying you today?"
            if persona == "mentor":
                return "Hello! Glad we're connecting. What's top of mind for you today?"
            return f"Hello! It's great to hear from you. What's on your mind today?"

        # 2. Food / Hungry / Tired
        if any(w in lower for w in ("eat", "food", "tired", "hungry", "exhausted", "sleep", "drain")):
            if persona == "mom":
                return "Oh beta, don't worry about anything right now. Sit down, rest your feet. I'll make you something warm and tasty to eat right away. Drink some water first, okay?"
            if persona == "dad":
                return "You worked hard today. Take a warm shower, get some good food into you, and let your mind rest. Everything else can wait until tomorrow."
            if persona == "best_friend":
                return "Man, you sound totally wiped out! Order some comfort food right now, put on your favorite show, and chill. You deserve a break!"
            if persona == "sibling":
                return "Dude, you look like a zombie! Go eat something before you collapse. Do you want me to order something for us?"
            if persona == "grandmother":
                return "Aha beta, health comes before everything else. Rest your eyes a little, eat some warm khichdi or fruit, and let Ammamma pat your head."
            if persona == "grandfather":
                return "Rest is not wasted time; it is the fuel for tomorrow's journey. Have a nourishing meal and sleep well tonight."
            if persona == "mentor":
                return "Listen to your body. When fatigue sets in, recovery is the most productive thing you can do. Recharge tonight and we can tackle the rest tomorrow."

        # 3. Success / Good news / Celebrations
        if any(w in lower for w in ("great", "happy", "won", "passed", "good", "promoted", "presentation", "celebrate", "awesome")):
            if persona == "mom":
                return "Sach me?! I am so, so proud of you, beta! Nazar na lage. We must make sweets and celebrate this!"
            if persona == "dad":
                return "Well done! I knew your hard work would pay off. Keep your feet on the ground, but definitely take a moment to be proud of yourself."
            if persona == "best_friend":
                return "LETS GOOO! I knew you'd crush it! We are 100% celebrating this weekend, party's on you!"
            if persona == "sibling":
                return "Whoa, look at you being all successful! Don't get too big-headed now, but seriously, that's awesome! Proud of you!"
            if persona == "grandmother":
                return "Bhagwan bless you, my child! My prayers are always with you. Keep shining like this."
            if persona == "mentor":
                return "Outstanding result. Take note of what worked well here -- that's a playbook you can reuse. Congratulations!"

        # 4. Stress / Sadness / Overwhelmed
        if any(w in lower for w in ("sad", "bad", "stressed", "cry", "angry", "worried", "anxious", "scared", "hate", "fight")):
            if persona == "mom":
                return "Achha, take a deep breath. Come here. Whatever it is, you don't have to carry it alone. Tell Mom slowly, I am listening."
            if persona == "dad":
                return "Take a moment. Tough times happen, but they pass. Let's break the problem down into small pieces and figure out a way forward together."
            if persona == "best_friend":
                return "Hey, that genuinely sucks and it's totally okay to feel mad or upset right now. Vent to me, I'm not going anywhere."
            if persona == "sibling":
                return "Hey... who messed with you? Tell me what happened. You know I've always got your back, no matter what."
            if persona == "grandmother":
                return "Arre beta, life has its sunny days and its cloudy days. Sit with me, hold my hand. Nothing is too heavy when shared."
            if persona == "mentor":
                return "Acknowledge the stress first -- don't push it away. Once the wave settles, what feels like the single most actionable thing right now?"

        # 5. Questions / Advice
        if "?" in clean or any(w in lower for w in ("why", "how", "what", "can you", "should i", "tell me")):
            if persona == "mom":
                return f"That's a thoughtful question, beta. In my experience, always trust your heart and don't rush. What does your gut instinct tell you about this?"
            if persona == "dad":
                return f"Good question. Look at both sides: what is the best outcome if you do it, and what's the worst if you don't? Weigh them rationally."
            if persona == "best_friend":
                return f"Honestly? If it were me, I'd go for it. But you know yourself best -- what's holding you back?"
            if persona == "sibling":
                return f"Hmm, tough call! If you ask me, keep it simple and don't overthink. Why are you stressing over it so much?"
            if persona == "grandmother":
                return f"Let Ammamma tell you something -- whatever decision brings peace to your heart is the right one. Don't worry about what others say."
            if persona == "grandfather":
                return f"A question well asked is half the answer found. What would you advise someone you care about in this exact situation?"
            if persona == "mentor":
                return f"That's the pivotal question. Let's look at the underlying principles rather than the immediate noise. What's the core objective here?"

        # 6. General fallback responding to user's text
        if persona == "best_friend":
            return f"Got you. About '{snippet}'... that makes a lot of sense. What do you think we should do next?"
        if persona == "mom":
            return f"I hear you, beta. I'm listening to everything you're saying about {snippet}. Tell me more, how does it make you feel?"
        if persona == "dad":
            return f"Understood. Let's look at {snippet} practically. What's the most important aspect of this right now?"
        if persona == "grandmother":
            return f"Acha beta, Ammamma understands. Tell me more, don't keep things locked in your heart."
        if persona == "grandfather":
            return f"Reflect on that for a second. Every experience teaches us something. What has this shown you?"
        if persona == "sibling":
            return f"Yeah, makes sense. So what's the next move? Are we doing something about it or just letting it ride?"
        if persona == "mentor":
            return f"That's an important insight. How does {snippet} align with where you want to be?"
        return f"I'm listening closely to what you're saying. Tell me more about that."

    async def transcribe(
        self, audio: bytes, *, filename: str, language_code: str, model: str, mode: str = "transcribe"
    ) -> STTResult:
        # Generate realistic transcribed phrases when offline
        phrases = [
            "Hey, how are you doing today?",
            "I had a really busy day today.",
            "Can you help me think through this?",
            "I am feeling a bit tired today.",
            "Tell me what you think about this.",
            "Hello, it's so good to talk to you."
        ]
        import random
        # Pick stable phrase based on audio length
        idx = (len(audio) // 300) % len(phrases)
        text = phrases[idx]
        return STTResult(text=text, language_code=language_code, mode=mode,
                         raw={"mock": True, "bytes": len(audio)})

    async def synthesize(
        self, text: str, *, language_code: str, speaker_id: str, model: str,
        pace: float = 1.0, sample_rate: int = 22050,
    ) -> TTSResult:
        audio = _tone_wav(text=text, speaker_id=speaker_id, sample_rate=sample_rate, pace=pace)
        return TTSResult(audio=audio, mime_type="audio/wav", sample_rate=sample_rate,
                         speaker_id=speaker_id, model="mock", raw={"mock": True})


def _tone_wav(*, text: str, speaker_id: str, sample_rate: int, pace: float) -> bytes:
    """A short, distinct-sounding WAV so playback and preview work offline."""
    digest = hashlib.sha256(speaker_id.encode()).digest()
    base_freq = 150 + (digest[0] % 12) * 35          # 150-535 Hz, stable per speaker
    duration = min(3.5, max(0.6, len(text) * 0.055)) / max(0.5, pace)
    n = int(sample_rate * duration)
    amp = 9000
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n):
            t = i / sample_rate
            env = math.sin(math.pi * min(1.0, t / 0.08)) * math.exp(-t / (duration * 0.9))
            vibrato = 1.0 + 0.02 * math.sin(2 * math.pi * 5 * t)
            sample = int(amp * env * math.sin(2 * math.pi * base_freq * vibrato * t))
            frames += struct.pack("<h", max(-32768, min(32767, sample)))
        w.writeframes(bytes(frames))
    return buf.getvalue()
