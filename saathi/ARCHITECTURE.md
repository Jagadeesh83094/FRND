# Architecture

## Layers

```
┌──────────────────────────────────────────────────────────────┐
│ Next.js frontend                                             │
│  • character selection, chat, customize, memories, onboarding │
│  • Live Talk: mic capture, playback, conversation state machine│
└───────────────▲──────────────────────────────┬───────────────┘
                │ JSON / multipart              │ (no API key here)
┌───────────────┴──────────────────────────────▼───────────────┐
│ FastAPI backend                                              │
│  routers → services → provider abstraction → Sarvam API      │
│  safety layer is applied to every prompt, for every character│
└───────────────────────────────┬──────────────────────────────┘
                                ▼
                        SQLite / Postgres
```

## Data model

New entities (requirement I) plus reused tables:

- **users** (reused) — identity + AI-disclosure acknowledgement.
- **character_definitions** — the built-in library. Content is versioned; a bump
  only changes the definition row, so **user customisations are never destroyed**.
- **user_characters** — a user's instance of a character: display name, nickname,
  language prefs, reply length, personality overrides, optional pinned voice.
  Unique on `(user_id, character_definition_id)`.
- **character_preferences** — flexible per-character settings (key/value JSON).
- **voice_configurations** — provider, model, speaker id, language, pace,
  fallback speaker, config version. Kept **separate from the chat prompt**.
- **character_conversations** — one independent thread per character.
- **messages** (reused) — turns, with language and a non-persistent audio ref.
- **memories** (reused) — user-owned facts, owned by an origin character by default.
- **conversation_memory_permissions** — explicit grants of a memory to another
  character. Unique on `(memory_id, granted_to_user_character_id)`.

Ownership is enforced in queries (every read is scoped by `user_id`), foreign keys
use `ON DELETE CASCADE`, and hot paths are indexed (`user_id`,
`user_character_id`, `conversation_id`).

### Why definitions and instances are separate

Built-in characters ship as `character_definitions`; a user's edits live in
`user_characters`. Updating the built-in library (new tone, better greeting) is a
row update on the definition and bumps its `version` — the user's rename, voice
choice and language prefs are untouched.

## Prompt composition

Every character's system prompt is assembled from four layers, in order:

1. **SAFETY_LAYER** — shared, non-negotiable (identity, honesty, emotional safety,
   health, privacy).
2. **SPOKEN_CONVERSATION** — how to talk out loud: short turns, contractions, no
   markdown read aloud, one question at a time, code-mixed speech, no repeated
   empathy phrases.
3. **The persona** — this character's description, style, structured tone profile
   (`warmth`, `playfulness`, `formality`, `directness`, `nurturing`,
   `reflectiveness`, `energy`), behaviours, and do/don't lists.
4. **Context** — only the memories this character is permitted to use, plus the
   crisis protocol when the message is flagged.

A custom character is *added on top of* layers 1 and 2 — never replaces them. The
custom validator rejects anything that tries to disable safety or impersonate a
real person, and clamps tone knobs to `[0, 1]`.

## Voice identity and fallback

Voice config is resolved by `resolve_voice(character_id, language)`:

1. A pinned user override wins.
2. Exact language, when a v4-flash persona exists → `bulbul:v4-flash`.
3. Malayalam / Odia (no v4 personas) → `bulbul:v3` short name.
4. Unsupported language → the character's primary-language persona.
5. Last resort → a v3 short name.

Every step reports whether it fell back and why, so the UI can say so. A persona
that the live API rejects (HTTP 400) is retried once on the stable v3 voice. The
curated catalog contains only IDs confirmed in the official docs.

## Conversation state machine (Live Talk)

```
idle → listening → transcribing → thinking → speaking → (listening | idle)
                     ▲                                   │
                     └──────────── interrupted ◄──────────┘
error is reachable from any step that can fail.
```

A monotonically increasing **turn id** is bumped on every new turn, interruption,
and unmount. Any async result whose turn id is stale is discarded, so a late
response can never play over a newer one and duplicate/out-of-order audio is
impossible. Interruption stops the player, aborts the in-flight fetch, and bumps
the id. Unmount (including a character switch) stops playback and releases the mic.

## Provider abstraction

`BaseProvider` defines `chat`, `transcribe`, and `synthesize`. Two implementations:

- **SarvamProvider** — live calls; maps HTTP failures to typed `ProviderError`
  kinds (timeout, rate_limit, network, credits, auth, bad_request, server), each
  with a user-safe message.
- **MockProvider** — offline; persona-aware replies and real WAV synthesis so the
  full flow runs and is testable without a key.

Switching providers is one env var (`PROVIDER_MODE`); nothing else changes.

## Memory model

- A memory is owned by the character it came from (`user_character_id`).
- `accessible_memories(character)` = its own memories ∪ memories explicitly
  granted to it.
- Intimate memories are never auto-shared.
- Controls: view who can access a memory, grant, revoke, delete one character's
  history, or delete all user data.
