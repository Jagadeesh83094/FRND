"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import type { Character, CharacterSession, CrisisInfo, Message } from "@/lib/types";
import { Avatar } from "@/components/Avatar";
import { CharacterSwitcher } from "@/components/CharacterSwitcher";
import { globalAudioPlayer, MicRecorder } from "@/lib/audio";

export default function ChatPage() {
  const params = useParams<{ characterId: string }>();
  const characterId = params.characterId;

  const [characters, setCharacters] = useState<Character[]>([]);
  const [session, setSession] = useState<CharacterSession | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [crisis, setCrisis] = useState<CrisisInfo | null>(null);
  
  // Live speaker options
  const [speakerEnabled, setSpeakerEnabled] = useState(true);
  const [playingMessageId, setPlayingMessageId] = useState<number | null>(null);

  // In-chat microphone recording
  const [isRecording, setIsRecording] = useState(false);
  const [micLevel, setMicLevel] = useState(0);
  const recorderRef = useRef<MicRecorder | null>(null);

  const endRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [chars, s] = await Promise.all([api.listCharacters(), api.getSession(characterId)]);
      setCharacters(chars);
      setSession(s);
      setMessages(s.messages);

      // Greet on a brand-new conversation
      if (s.messages.length === 0) {
        const g = await api.greeting(characterId, speakerEnabled);
        setMessages((m) => [
          ...m,
          {
            id: g.message_id,
            role: "assistant",
            content: g.reply,
            created_at: new Date().toISOString(),
            meta: { audio_base64: g.audio_base64, audio_mime: g.audio_mime },
          },
        ]);
        if (speakerEnabled) {
          if (g.audio_base64) {
            setPlayingMessageId(g.message_id);
            void globalAudioPlayer.play(g.audio_base64, g.audio_mime || "audio/wav").finally(() => {
              setPlayingMessageId(null);
            });
          } else {
            setPlayingMessageId(g.message_id);
            void globalAudioPlayer.speakText(g.reply).finally(() => setPlayingMessageId(null));
          }
        }
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }, [characterId, speakerEnabled]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    return () => {
      globalAudioPlayer.stop();
      recorderRef.current?.release();
    };
  }, []);

  async function playAssistantMessage(msgId: number, content: string, audioBase64?: string, audioMime?: string) {
    if (playingMessageId === msgId) {
      globalAudioPlayer.stop();
      setPlayingMessageId(null);
      return;
    }

    setPlayingMessageId(msgId);
    try {
      if (audioBase64) {
        await globalAudioPlayer.play(audioBase64, audioMime || "audio/wav");
      } else {
        // Request TTS from backend or fallback to browser speech
        try {
          const res = await api.tts(characterId, content);
          if (res.audio_base64) {
            await globalAudioPlayer.play(res.audio_base64, res.mime_type || "audio/wav");
          } else {
            await globalAudioPlayer.speakText(content);
          }
        } catch {
          await globalAudioPlayer.speakText(content);
        }
      }
    } catch (e) {
      console.warn("Audio play error, falling back to speech synthesis", e);
      await globalAudioPlayer.speakText(content);
    } finally {
      setPlayingMessageId(null);
    }
  }

  async function send(customText?: string, mode: "text" | "voice" = "text") {
    const text = (customText !== undefined ? customText : input).trim();
    if (!text || sending) return;
    if (customText === undefined) setInput("");
    setSending(true);
    setCrisis(null);

    const tempId = Date.now();
    const optimistic: Message = {
      id: tempId,
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((m) => [...m, optimistic]);

    try {
      const turn = await api.chat(characterId, {
        text,
        mode,
        speak: speakerEnabled,
      });

      const assistantMsg: Message = {
        id: turn.message_id,
        role: "assistant",
        content: turn.reply,
        created_at: new Date().toISOString(),
        meta: {
          memories_used: turn.memories_used,
          audio_base64: turn.audio_base64,
          audio_mime: turn.audio_mime,
        },
      };

      setMessages((m) => [...m, assistantMsg]);
      if (turn.crisis.flagged) setCrisis(turn.crisis);

      // Play through speaker live
      if (speakerEnabled) {
        if (turn.audio_base64) {
          setPlayingMessageId(turn.message_id);
          void globalAudioPlayer.play(turn.audio_base64, turn.audio_mime || "audio/wav").finally(() => {
            setPlayingMessageId(null);
          });
        } else {
          setPlayingMessageId(turn.message_id);
          void globalAudioPlayer.speakText(turn.reply).finally(() => {
            setPlayingMessageId(null);
          });
        }
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSending(false);
    }
  }

  async function toggleRecording() {
    if (isRecording) {
      // Stop and transcribe
      setIsRecording(false);
      setSending(true);
      try {
        const blob = await recorderRef.current!.stop();
        if (blob && blob.size > 800) {
          const lang = session?.character.language_prefs?.[0] || "en-IN";
          const res = await api.transcribe(blob, lang);
          if (res.text && res.text.trim()) {
            await send(res.text.trim(), "voice");
          }
        }
      } catch (err) {
        setError("Transcription failed: " + (err as Error).message);
      } finally {
        setSending(false);
      }
    } else {
      // Start recording
      setError(null);
      if (!recorderRef.current) recorderRef.current = new MicRecorder();
      try {
        await recorderRef.current.start((lvl) => setMicLevel(lvl));
        setIsRecording(true);
      } catch (err) {
        setError("Microphone error: " + (err as Error).message);
      }
    }
  }

  const character = session?.character;

  return (
    <main>
      <div className="spread" style={{ marginBottom: 16 }}>
        <div className="row">
          {character && <Avatar characterId={character.id} avatarRef={character.avatar_ref} size={46} />}
          <div>
            <div style={{ fontWeight: 700 }}>{character?.display_name || "…"}</div>
            <div className="muted">
              {character?.conversational_style?.slice(0, 70) || "Independent conversation"}
            </div>
          </div>
        </div>
        <div className="row" style={{ gap: 8 }}>
          {characters.length > 0 && (
            <CharacterSwitcher characters={characters} currentId={characterId} />
          )}

          {/* Speaker toggle */}
          <button
            className={`btn btn-sm ${speakerEnabled ? "btn-primary" : "btn-ghost"}`}
            onClick={() => {
              const next = !speakerEnabled;
              setSpeakerEnabled(next);
              if (!next) globalAudioPlayer.stop();
            }}
            title={speakerEnabled ? "Live speaker playback enabled" : "Speaker muted"}
            aria-label="Toggle live speaker"
          >
            {speakerEnabled ? "🔊 Speaker: ON" : "🔈 Speaker: OFF"}
          </button>

          {/* Live Call Mode button */}
          <Link
            className="btn btn-sm"
            style={{
              background: "linear-gradient(135deg, rgba(255,138,91,0.25), rgba(255,196,107,0.3))",
              borderColor: "var(--accent)",
              fontWeight: 600,
            }}
            href={`/live/${characterId}`}
          >
            🎙️ Live Voice Call
          </Link>
          <Link className="btn btn-sm btn-ghost" href={`/customize/${characterId}`}>Edit</Link>
        </div>
      </div>

      <div className="row" style={{ gap: 8, marginBottom: 10 }}>
        <span className="pill">{session?.memory_count ?? 0} shared memories</span>
        {character?.voice && <span className="pill">Voice: {character.voice.speaker_id}</span>}
        <span className={`pill ${speakerEnabled ? "good" : ""}`}>
          {speakerEnabled ? "Live audio enabled" : "Muted audio"}
        </span>
      </div>

      {error && <div className="notice bad" style={{ marginBottom: 10 }}>{error}</div>}
      {crisis?.flagged && (
        <div className="notice warn" style={{ marginBottom: 10 }}>
          It sounds like things are really hard right now. If you're in crisis, please reach out:
          {" "}
          {crisis.resources.map((r, i) => (
            <span key={r.contact}>
              {i > 0 ? " · " : ""}
              {r.name}: <strong>{r.contact}</strong>
            </span>
          ))}
        </div>
      )}

      <div className="chat-wrap">
        <div className="messages">
          {messages.map((m) => {
            const isPlaying = playingMessageId === m.id;
            return (
              <div
                key={m.id}
                className={`bubble ${m.role === "user" ? "user" : "assistant"}`}
                style={{ position: "relative" }}
              >
                <div>{m.content}</div>
                {m.role === "assistant" && (
                  <div style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 8 }}>
                    <button
                      type="button"
                      onClick={() =>
                        void playAssistantMessage(
                          m.id,
                          m.content,
                          (m.meta as { audio_base64?: string })?.audio_base64,
                          (m.meta as { audio_mime?: string })?.audio_mime
                        )
                      }
                      style={{
                        padding: "3px 8px",
                        fontSize: 12,
                        borderRadius: 8,
                        background: isPlaying ? "var(--accent)" : "rgba(255,255,255,0.08)",
                        color: isPlaying ? "#000" : "var(--text)",
                        border: "1px solid var(--border)",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                      }}
                      title="Play message on speaker"
                    >
                      {isPlaying ? "⏹ Stop" : "🔊 Listen"}
                    </button>
                    {isPlaying && <span className="muted" style={{ fontSize: 11 }}>Speaking...</span>}
                  </div>
                )}
              </div>
            );
          })}
          {sending && (
            <div className="bubble assistant muted" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span>Thinking &amp; generating voice…</span>
            </div>
          )}
          <div ref={endRef} />
        </div>

        {/* Live Audio Meter during Recording */}
        {isRecording && (
          <div
            className="row"
            style={{
              padding: "8px 14px",
              background: "rgba(255, 75, 75, 0.15)",
              border: "1px solid rgba(255, 75, 75, 0.4)",
              borderRadius: 12,
              marginBottom: 8,
              justifyContent: "space-between",
            }}
          >
            <div className="row" style={{ gap: 8 }}>
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: "#ff4b4b",
                  boxShadow: "0 0 10px #ff4b4b",
                  animation: "pulse 1s infinite",
                }}
              />
              <span style={{ fontWeight: 600, fontSize: 13, color: "#ff8a8a" }}>
                Listening to your voice... Speak now!
              </span>
            </div>
            <div style={{ width: 120, height: 8, background: "rgba(255,255,255,0.1)", borderRadius: 4, overflow: "hidden" }}>
              <div
                style={{
                  width: `${Math.min(100, Math.max(10, micLevel * 100))}%`,
                  height: "100%",
                  background: "linear-gradient(90deg, #ff8a5b, #ff4b4b)",
                  transition: "width 0.1s ease",
                }}
              />
            </div>
          </div>
        )}

        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
        >
          {/* In-chat Microphone button */}
          <button
            type="button"
            className="btn"
            onClick={() => void toggleRecording()}
            style={{
              padding: "0 16px",
              background: isRecording
                ? "linear-gradient(135deg, #ff4b4b, #ff8a5b)"
                : "var(--surface)",
              color: isRecording ? "#fff" : "var(--text)",
              fontSize: 18,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
            title={isRecording ? "Stop recording and send" : "Speak message with microphone"}
            aria-label="Microphone"
          >
            {isRecording ? "⏹" : "🎙"}
          </button>

          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              isRecording
                ? "Recording voice... Click ⏹ when finished"
                : `Message ${character?.display_name || ""}…`
            }
            aria-label="Message"
            disabled={isRecording}
          />
          <button className="btn-primary" type="submit" disabled={sending || !input.trim() || isRecording}>
            Send
          </button>
        </form>
      </div>
    </main>
  );
}
