from __future__ import annotations

from uuid import uuid4


def test_register_login_and_bearer_access(client):
    email = f"auth-{uuid4().hex}@example.test"
    password = "a-long-unique-password-123"
    registered = client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "display_name": "Auth test",
    })
    assert registered.status_code == 201, registered.text
    token = registered.json()["access_token"]
    assert registered.json()["email"] == email

    login = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    protected = client.get("/api/characters", headers={"Authorization": f"Bearer {token}"})
    assert protected.status_code == 200, protected.text
    assert protected.json()


def test_login_rejects_wrong_password(client):
    email = f"auth-{uuid4().hex}@example.test"
    registered = client.post("/api/auth/register", json={"email": email, "password": "another-strong-password"})
    assert registered.status_code == 201
    response = client.post("/api/auth/login", json={"email": email, "password": "wrong-password"})
    assert response.status_code == 401
