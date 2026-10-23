# FRND — Saathi AI

This repository contains **Saathi**, a voice-first multilingual AI companion with selectable fictional conversational characters.

The application source currently lives in the saathi/ directory.

## Start here

- [Project overview and setup](saathi/README.md)
- [Architecture](saathi/ARCHITECTURE.md)
- [Safety notes](saathi/docs/SAFETY.md)
- [Acceptance tests](saathi/ACCEPTANCE_TESTS.md)

## Important security status

The current X-User-Email identity adapter is for local development only. Production mode now fails closed for protected user routes until a real authentication provider is integrated. Do not deploy publicly with ENVIRONMENT=development.

The in-process rate limiter is a basic guard for local/single-worker use, not a replacement for an edge/API gateway limit or a shared limiter in a multi-worker deployment. Keep Sarvam credentials in backend environment secrets; never commit real keys.

## Repository layout

- saathi/backend/ — FastAPI API, database, provider integration, tests
- saathi/frontend/ — Next.js UI
- saathi/docs/ — project safety and design documentation
