"""Chat, turn-taking, history isolation and voice fallback (requirements C, E, F, G)."""
from __future__ import annotations


def _chat(client, headers, character, text, **kw):
    r = client.post(f"/api/characters/{character}/chat", json={"text": text, **kw}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_turn_produces_reply_and_persists(client, user_headers):
    out = _chat(client, user_headers, "best_friend", "Hey, long time!")
    assert out["reply"]
    assert out["message_id"]
    assert out["conversation_id"]
    msgs = client.get(
        f"/api/conversations/{out['conversation_id']}/messages", headers=user_headers
    ).json()
    roles = [m["role"] for m in msgs]
    assert "user" in roles and "assistant" in roles


def test_different_characters_produce_different_styles(client, user_headers):
    friend = _chat(client, user_headers, "best_friend", "Bro, today was terrible")["reply"]
    mom = _chat(client, user_headers, "mom", "Bro, today was terrible")["reply"]
    mentor = _chat(client, user_headers, "mentor", "Bro, today was terrible")["reply"]
    assert friend != mom and mom != mentor and friend != mentor
    # persona-flavoured, not generic
    assert "beta" in mom.lower() or "come here" in mom.lower()


def test_history_is_separate_per_character(client, user_headers):
    secret = "I got the placement offer at Acme Corp"
    _chat(client, user_headers, "best_friend", secret)

    friend_session = client.get("/api/characters/best_friend/session", headers=user_headers).json()
    mom_session = client.get("/api/characters/mom/session", headers=user_headers).json()

    friend_text = " ".join(m["content"] for m in friend_session["messages"])
    mom_text = " ".join(m["content"] for m in mom_session["messages"])

    assert "Acme Corp" in friend_text
    assert "Acme Corp" not in mom_text  # private context never leaks across characters


def test_greeting_uses_character_voice_line(client, user_headers):
    r = client.post("/api/characters/grandmother/greeting", headers=user_headers)
    assert r.status_code == 200
    assert r.json()["reply"]


def test_voice_resolution_falls_back_safely():
    from app.voice_catalog import resolve_voice

    # A character with no persona for the requested language falls back.
    r = resolve_voice("best_friend", "fr-FR")
    assert r["fallback"] is not None
    assert r["speaker_id"]

    # Malayalam has no v4 persona -> must use bulbul:v3 with a v3 short name.
    r = resolve_voice("best_friend", "ml-IN")
    assert r["model"] == "bulbul:v3"
    assert r["fallback"] is not None

    # A normal v4 language resolves cleanly.
    r = resolve_voice("best_friend", "te-IN")
    assert r["model"] == "bulbul:v4-flash"
    assert r["fallback"] is None
