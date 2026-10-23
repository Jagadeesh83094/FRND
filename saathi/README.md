# Saathi

Saathi is a voice-first multilingual AI companion with fictional conversational characters, per-character conversations, configurable voices, and optional user-controlled memories.

## Security status

**Local development only until real authentication is integrated.** The current X-User-Email header is a development identity stub, not proof of identity. Protected user routes fail closed when ENVIRONMENT=production. Do not make the API public with ENVIRONMENT=development.

See [Security and deployment checklist](SECURITY.md) before deploying.

## Repository map

- backend/ — FastAPI, SQLAlchemy, Alembic, Sarvam and mock providers
- frontend/ — Next.js application
- ARCHITECTURE.md — system overview
- ACCEPTANCE_TESTS.md — expected application behavior

## Local development

1. Configure backend variables from backend/.env.example.
2. Configure frontend variables from frontend/.env.local.example.
3. Start the backend from backend/ with the project's documented ASGI command.
4. Start the frontend from frontend/ using npm install and npm run dev.

The mock provider can be used for local development without spending Sarvam credits. Keep the Sarvam key only in the backend environment.
