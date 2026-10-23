"""Memory architecture and sharing-permission tests (requirement F)."""
from __future__ import annotations


def _uc_id(client, headers, character):
    chars = client.get("/api/characters", headers=headers).json()
    return next(c["user_character_id"] for c in chars if c["id"] == character)


def _session_memories(client, headers, character):
    return client.get(f"/api/characters/{character}/session", headers=headers).json()["memories"]


def test_memory_is_private_to_its_character_by_default(client, user_headers):
    r = client.post(
        "/api/memories/for-character/mom",
        json={"content": "Placement interview on Friday", "category": "event"},
        headers=user_headers,
    )
    assert r.status_code == 201
    assert _session_memories(client, user_headers, "mom")  # mom sees it
    dad = _session_memories(client, user_headers, "dad")
    assert all("Placement interview on Friday" != m["content"] for m in dad)  # dad does not


def test_granting_a_memory_shares_it_and_revoking_removes_it(client, user_headers):
    mem = client.post(
        "/api/memories/for-character/mom",
        json={"content": "Upcoming exam on 5 Nov", "category": "event"},
        headers=user_headers,
    ).json()
    dad_id = _uc_id(client, user_headers, "dad")

    g = client.post(
        "/api/memories/grant",
        json={"memory_id": mem["id"], "user_character_id": dad_id},
        headers=user_headers,
    )
    assert g.status_code == 200
    assert dad_id in g.json()["shared_with"]
    assert any(m["content"] == "Upcoming exam on 5 Nov" for m in _session_memories(client, user_headers, "dad"))

    rv = client.post(
        "/api/memories/revoke",
        json={"memory_id": mem["id"], "user_character_id": dad_id},
        headers=user_headers,
    )
    assert rv.status_code == 200
    assert dad_id not in rv.json()["shared_with"]
    assert all(m["content"] != "Upcoming exam on 5 Nov" for m in _session_memories(client, user_headers, "dad"))


def test_intimate_memory_is_not_shared_automatically(client, user_headers):
    mem = client.post(
        "/api/memories/for-character/best_friend",
        json={"content": "Something very private", "sensitivity": "intimate"},
        headers=user_headers,
    ).json()
    assert mem["sensitivity"] == "intimate"
    # Even after creating it, no other character sees it.
    for other in ("mom", "dad", "mentor"):
        assert all("Something very private" != m["content"] for m in _session_memories(client, user_headers, other))


def test_shared_memory_visible_to_selected_characters_only(client, user_headers):
    mom_id = _uc_id(client, user_headers, "mom")
    mentor_id = _uc_id(client, user_headers, "mentor")
    client.post(
        "/api/memories",
        json={"content": "Shared: I love cricket", "share_with": [mom_id, mentor_id]},
        headers=user_headers,
    )
    assert any(m["content"] == "Shared: I love cricket" for m in _session_memories(client, user_headers, "mom"))
    assert any(m["content"] == "Shared: I love cricket" for m in _session_memories(client, user_headers, "mentor"))
    assert all(m["content"] != "Shared: I love cricket" for m in _session_memories(client, user_headers, "dad"))


def test_delete_character_history(client, user_headers):
    client.post("/api/characters/sibling/chat", json={"text": "hi"}, headers=user_headers)
    client.post(
        "/api/memories/for-character/sibling",
        json={"content": "temp memory"},
        headers=user_headers,
    )
    r = client.delete("/api/characters/sibling/history", headers=user_headers)
    assert r.status_code == 200
    session = client.get("/api/characters/sibling/session", headers=user_headers).json()
    assert session["messages"] == []
    assert session["memories"] == []


def test_delete_all_user_data(client, second_user_headers):
    client.post("/api/characters/mom/chat", json={"text": "hello"}, headers=second_user_headers)
    r = client.delete("/api/user/data", headers=second_user_headers)
    assert r.status_code == 200
    # Conversations are gone; a fresh session starts empty.
    session = client.get("/api/characters/mom/session", headers=second_user_headers).json()
    assert session["messages"] == []
