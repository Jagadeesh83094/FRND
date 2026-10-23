"""Minimal account authentication helpers.

Tokens are HMAC-signed, time-limited bearer tokens. Passwords are hashed with
PBKDF2-HMAC-SHA256 and a unique random salt. Use a managed identity provider
for email verification, recovery, MFA and larger production deployments.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import HTTPException

PBKDF2_ITERATIONS = 600_000
TOKEN_TTL_SECONDS = 60 * 60 * 12


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256\u0024{PBKDF2_ITERATIONS}\u0024{_b64(salt)}\u0024{_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = stored.split("\u0024", 3)
        iteration_count = int(iterations)
        # Stored hashes can be corrupted or tampered with; never allow their
        # iteration count to trigger an unbounded CPU-expensive verification.
        if algorithm != "pbkdf2_sha256" or not 100_000 <= iteration_count <= 1_000_000:
            return False
        salt = base64.urlsafe_b64decode(salt_text + "=" * (-len(salt_text) % 4))
        expected = base64.urlsafe_b64decode(digest_text + "=" * (-len(digest_text) % 4))
        if len(salt) != 16 or len(expected) != 32:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iteration_count)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def issue_access_token(user_id: int, secret_key: str) -> str:
    if len(secret_key) < 32:
        raise HTTPException(status_code=503, detail="Authentication secret must be configured (32+ characters)")
    now = int(time.time())
    payload = _b64(json.dumps({"sub": str(user_id), "iat": now, "exp": now + TOKEN_TTL_SECONDS}, separators=(",", ":")).encode())
    signing_input = f"saathi-v1.{payload}".encode()
    signature = hmac.new(secret_key.encode(), signing_input, hashlib.sha256).digest()
    return f"saathi-v1.{payload}.{_b64(signature)}"


def verify_access_token(token: str, secret_key: str) -> int:
    try:
        version, payload_text, signature_text = token.split(".", 2)
        if version != "saathi-v1" or len(secret_key) < 32:
            raise ValueError("invalid token")
        signing_input = f"{version}.{payload_text}".encode()
        signature = base64.urlsafe_b64decode(signature_text + "=" * (-len(signature_text) % 4))
        expected = hmac.new(secret_key.encode(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        payload_bytes = base64.urlsafe_b64decode(payload_text + "=" * (-len(payload_text) % 4))
        payload = json.loads(payload_bytes)
        now = int(time.time())
        issued_at = int(payload["iat"])
        expires_at = int(payload["exp"])
        if issued_at > now + 60 or expires_at <= now or expires_at <= issued_at:
            raise ValueError("invalid token lifetime")
        if expires_at - issued_at > TOKEN_TTL_SECONDS:
            raise ValueError("token lifetime too long")
        user_id = int(payload["sub"])
        if user_id <= 0:
            raise ValueError("invalid subject")
        return user_id
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired access token") from exc
