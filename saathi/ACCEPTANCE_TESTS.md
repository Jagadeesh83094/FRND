# Acceptance tests

How each requirement from the brief is satisfied, and where it is verified.

| # | Criterion | Where | Test |
| --- | --- | --- | --- |
| 1 | Select a character and start a conversation | `frontend/src/app/page.tsx`, `chat/[characterId]/page.tsx` | `test_turn_produces_reply_and_persists`, `test_greeting_uses_character_voice_line` |
| 2 | Different characters produce different styles | `characters.py` personas + prompt layering | `test_different_characters_produce_different_styles`, `test_personalities_are_genuinely_distinct` |
| 3 | Each character is audible with a supported voice | `voice_catalog.py`, `/voice-preview` | `test_every_character_has_a_supported_voice`, `test_voice_preview_returns_playable_audio` |
| 4 | Speak and receive an audible response | `useVoiceSession.ts`, `/voice/transcribe`, `/chat?speak` | `test_transcribe_accepts_audio_and_returns_text`, `test_chat_turn_can_include_audio` |
| 5 | Next turn starts without manual submission | auto-listen in `useVoiceSession.ts` | covered by state-machine flow; auto-listen toggle in Live Talk |
| 6 | Interrupt or stop audio | `interrupt()` in `useVoiceSession.ts`, ✋ control | turn-id guard + `player.stop()` (design verified in code) |
| 7 | Push-to-talk fallback | `pttMode` in `live/[characterId]/page.tsx` | hold mic / space bar; `pushToTalkStart/End` |
| 8 | Conversation history separate by character | `character_conversations` | `test_history_is_separate_per_character` |
| 9 | Switching does not mix private histories | per-character sessions + teardown on unmount | `test_history_is_separate_per_character` |
| 10 | Language and voice settings persist | `user_characters`, `voice_configurations` | `test_language_preference_persists` |
| 11 | Unavailable voices trigger a safe fallback | `resolve_voice` | `test_voice_resolution_falls_back_safely` |
| 12 | Mic denial and API failures handled gracefully | `MicRecorder`, typed `ProviderError` | `test_voice_config_reports_turn_based_and_provider` + error paths |
| 13 | Safety behaviour consistent across characters | `safety.py` shared layer | `test_safety_layer_is_present_in_every_character_prompt`, `test_crisis_reply_keeps_warm_tone_and_offers_help` |
| 14 | Tests verify memory-sharing permissions | `memory_service.py` | `test_memory_is_private_to_its_character_by_default`, `test_granting_a_memory_shares_it_and_revoking_removes_it`, `test_intimate_memory_is_not_shared_automatically`, `test_shared_memory_visible_to_selected_characters_only` |
| 15 | Runs locally and passes the production build | `npm run build` | 7 routes compiled + type-checked; `pytest -q` → 36 passed |

## Run everything

```bash
cd backend && . .venv/bin/activate && pytest -q          # 36 passed
cd ../frontend && ulimit -v unlimited && npm run build    # build passes
```

## Notes on what is *not* claimed

- Live Talk is **turn-based** (record → transcribe → reply → speak), not
  continuous real-time duplex audio. The UI states this explicitly.
- The offline mock provider returns a canned transcript (it cannot recover words
  from audio) and persona-flavoured replies; it exists so the pipeline is
  runnable and testable without a Sarvam key.
