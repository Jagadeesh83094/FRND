# Saathi security and deployment checklist

## Current status

- X-User-Email is a development identity stub, not authentication.
- Protected user routes return 503 when ENVIRONMENT=production until a verified identity provider is integrated.
- The in-process request limiter is for local/single-worker use only and is not shared across workers or replicas.
- Review whether public health and voice-config endpoints expose acceptable operational metadata.
- Do not expose the app publicly while development identity mode is enabled.

## Account authentication added on the hardening branch

The branch now includes email/password registration and login, salted PBKDF2-HMAC-SHA256 password hashes, and 12-hour HMAC-signed bearer tokens. Production protected routes require a valid token and a configured AUTH_SECRET_KEY. The fallback signing key is for development only.

This is an initial account-auth layer, not yet a complete public identity system: email verification, password reset, MFA, refresh/revocation, and account recovery are not implemented. Do not open public registration broadly until verification/recovery and operational controls are added, or replace this with a managed identity provider.

## Before public deployment

1. Integrate a real identity provider (verified server-side session or JWT); validate issuer, audience and expiry. Derive user identity from verified claims, not a caller-supplied email header.
2. Remove the frontend NEXT_PUBLIC_USER_EMAIL identity mechanism and send only verified session credentials.
3. Use a shared rate limiter or API gateway for chat, transcription, TTS and preview endpoints. Enforce quotas and upload limits at the edge too.
4. Configure exact production CORS origins; do not use wildcard origins with credentials.
5. Use a persistent managed database and run Alembic migrations as a deployment step. Production startup intentionally does not call `create_all`; the deploy command must run `alembic upgrade head`.
6. Store SARVAM_API_KEY only in backend secret storage. Never expose it in NEXT_PUBLIC variables or commit it.
7. Keep raw-audio persistence disabled unless explicitly needed and consented to.
8. Run backend tests, frontend build, dependency/security scans and live-provider smoke tests before release.
9. Avoid logging API keys, raw audio or sensitive conversation content.
10. Rotate any credential ever committed to Git history; deleting a file alone does not invalidate it.

## Rate-limiter caveat

The built-in limiter uses in-memory state keyed by the direct client address. Behind a reverse proxy, configure trusted proxy handling carefully; do not trust arbitrary forwarded headers. Replace this limiter with Redis or gateway controls for multi-worker deployments.
