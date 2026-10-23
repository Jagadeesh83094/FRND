# Saathi — multi-character, voice-first AI companion

Saathi is a companionship app where you choose **who** you want to talk to — a best
friend, mom, dad, grandmother, grandfather, a sibling, a calm mentor, or a character
you design yourself. Each character has a genuinely distinct personality, its own
voice, and its own private conversation history.

Voice is a first-class experience, not a decoration: a full-screen **Live Talk**
mode lets you speak and hear a reply, turn by turn.

> Every character is an AI-generated companion. They are fictional and inspired by
> broad conversational styles — not your real family, not real people, and with no
> genuine memories. They are not a substitute for the people in your life or for
> professional care.

---

## What's in the box

| Area | What it does |
| --- | --- |
| Character library | 8 built-ins (best friend, mom, dad, grandmother, grandfather, sibling, mentor, custom) |
| Distinct personalities | Each is its own prompt + structured tone profile — not a word swap |
| Voice-first Live Talk | Full-screen voice UI with listening / thinking / speaking states, waveform, interruption, push-to-talk |
| Text chat | Independent per-character conversation, with greeting and crisis handling |
| Customisation | Rename, regional names, languages, reply length, voice, personality |
| Voice identity | Stored separately from the prompt, with real Sarvam speaker IDs and safe fallback |
| Memory + permissions | Per-character by default; explicit, revocable sharing; full delete controls |
| Safety layer | Shared, non-removable rules on every character; crisis protocol with Indian helplines |
| Persistence | Normalised schema + Alembic migrations |

## Architecture at a glance

```
frontend/  Next.js (App Router, TypeScript)   — UI, voice capture/playback, state machine
backend/   FastAPI + SQLAlchemy + Alembic     — characters, chat, memory, voice, safety
           └─ provider abstraction            — SarvamProvider (live) | MockProvider (offline)
```

The **Sarvam API key lives only on the backend** and is never sent to the browser.

### Sarvam models used

| Capability | Model | Endpoint |
| --- | --- | --- |
| Chat | `sarvam-105b-conversations` (dialogue-tuned), `sarvam-105b` | `POST /v1/chat/completions` |
| Speech-to-text | `saaras:v4` (modes: transcribe / translate / verbatim / translit / codemix) | `POST /speech-to-text` |
| Text-to-speech | `bulbul:v4-flash` (persona voices), `bulbul:v3` (fallback, incl. Malayalam/Odia) | `POST /text-to-speech` |

Voice IDs are the real, documented ones (e.g. `sunny_en_social`,
`aparna_en_companion`, `kavitha_te_conversation`). v4-flash IDs follow
`voice_language_style`; v3 short names (like `shubh`) are rejected on v4, and
Malayalam/Odia have no v4 personas — so those languages fall back to `bulbul:v3`.

---

## Running it locally

You need Python 3.11+ and Node 20+.

### 1. Backend

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then put your key in SARVAM_API_KEY (optional)
alembic upgrade head        # create the schema
python seed.py              # seed the built-in character library

uvicorn app.main:app --reload --port 8000
```

**No key? It still works.** With `SARVAM_API_KEY` empty (or `PROVIDER_MODE=mock`)
the app runs on an offline mock provider: persona-distinct replies and real,
playable WAV audio so you can exercise the whole flow. The UI labels this
"Offline mock mode".

> Note: `ulimit -v` must not be too low for `next build` (Next's WASM needs address
> space). If your shell caps virtual memory, run `ulimit -v unlimited` first.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # points at http://localhost:8000
npm run dev                        # http://localhost:3000
```

Production build:

```bash
npm run build && npm run start
```

### One-shot dev helper

From the repo root:

```bash
bash run.sh       # starts backend (:8000) and frontend (:3000)
```

---

## Tests

```bash
cd backend && . .venv/bin/activate && pytest -q     # 36 tests
```

The suite is mapped to the acceptance criteria — see [`ACCEPTANCE_TESTS.md`](ACCEPTANCE_TESTS.md).

---

## How voice works (honest description)

Live Talk is **turn-based**, not continuous real-time audio:

1. You speak; the browser records with `MediaRecorder`.
2. On end-of-speech (auto) or button release (push-to-talk), the clip is uploaded.
3. Saaras transcribes it.
4. The transcript plus permitted context goes to the chat model.
5. The reply is synthesized with Bulbul and played back.
6. The app returns to listening (auto mode) or waits for your next push.

The UI says so plainly rather than pretending to be continuous duplex audio. A
real-time WebSocket path (`saaras:v3-realtime`) is the natural next step and is
noted in the code.

Interruption is handled properly: pressing interrupt or starting a new turn stops
playback immediately, aborts the in-flight request, and bumps a turn counter so a
late or out-of-order response can never play over a newer one.

## Privacy defaults

- Raw audio is **never persisted** (`PERSIST_RAW_AUDIO=false`); only the transcript is stored.
- Memories belong to the character they came from. Sharing is explicit and revocable.
- Intimate memories are never auto-shared between characters.
- You can delete a single character's history or all of your data.

## Project layout

```
backend/
  app/
    characters.py      personality library (8 characters)
    safety.py          shared safety layer, crisis detection, custom validation
    prompts.py         prompt composition + speech sanitiser
    voice_catalog.py   real voice IDs + character→voice map + fallback
    providers/         base | sarvam (live) | mock (offline)
    services/          character, conversation, memory, chat, voice
    routers/           characters, chat, conversations, memories, voice, onboarding
    models.py          schema (6 new entities + reused users/messages/memories)
  migrations/          Alembic
  tests/               36 tests
frontend/
  src/app/             home, chat, live, customize, memories, onboarding
  src/components/      avatar, cards, switcher, waveform, voice preview
  src/lib/             api client, types, audio, useVoiceSession (state machine)
```
