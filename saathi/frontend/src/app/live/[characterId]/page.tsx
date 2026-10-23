"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Character, VoiceConfigInfo } from "@/lib/types";
import { useVoiceSession } from "@/lib/useVoiceSession";
import { Avatar } from "@/components/Avatar";
import { Waveform, statusLabel } from "@/components/Waveform";

const LANGUAGES = [
  { code: "en-IN", label: "English" },
  { code: "hi-IN", label: "हिन्दी (Hindi)" },
  { code: "te-IN", label: "తెలుగు (Telugu)" },
  { code: "ta-IN", label: "தமிழ் (Tamil)" },
  { code: "kn-IN", label: "ಕನ್ನಡ (Kannada)" },
  { code: "bn-IN", label: "বাংলা (Bengali)" },
  { code: "mr-IN", label: "मराठी (Marathi)" },
  { code: "ml-IN", label: "മലയാളം (Malayalam)" },
];

export default function LiveTalkPage() {
  const params = useParams<{ characterId: string }>();
  const router = useRouter();
  const characterId = params.characterId;

  const [character, setCharacter] = useState<Character | null>(null);
  const [cfg, setCfg] = useState<VoiceConfigInfo | null>(null);
  const [language, setLanguage] = useState<string | undefined>(undefined);
  const [showSettings, setShowSettings] = useState(false);
  const [pttMode, setPttMode] = useState(false); // push-to-talk fallback
  const [crisis, setCrisis] = useState<{ flagged: boolean; resources: { name: string; contact: string }[] } | null>(null);

  const session = useVoiceSession({
    characterId,
    language,
    onTurn: ({ crisis: isCrisis }) => {
      if (isCrisis) setCrisis({ flagged: true, resources: [] });
    },
  });

  useEffect(() => {
    Promise.all([api.getSession(characterId), api.voiceConfig()])
      .then(([s, info]) => {
        setCharacter(s.character);
        setCfg(info);
        setLanguage(s.character.language_prefs?.[0] || s.character.languages?.[0]);
        session.setMessages(s.messages);
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [characterId]);

  // Load crisis resources for the banner
  useEffect(() => {
    if (!crisis?.flagged) return;
    setCrisis({
      flagged: true,
      resources: [
        { name: "Tele-MANAS", contact: "14416" },
        { name: "KIRAN", contact: "1800-599-0019" },
      ],
    });
  }, [crisis?.flagged]);

  const exit = useCallback(() => {
    session.end();       // stop playback + release mic
    router.push(`/chat/${characterId}`);
  }, [characterId, router, session]);

  // spacebar hold = push-to-talk
  useEffect(() => {
    if (!pttMode) return;
    function down(e: KeyboardEvent) {
      if (e.code === "Space" && !e.repeat) {
        e.preventDefault();
        void session.pushToTalkStart();
      }
    }
    function up(e: KeyboardEvent) {
      if (e.code === "Space") {
        e.preventDefault();
        void session.pushToTalkEnd();
      }
    }
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
    };
  }, [pttMode, session]);

  const listening = session.state === "listening";
  const speaking = session.state === "speaking";
  const busy = session.state === "thinking" || session.state === "transcribing";

  const lastAssistant = [...session.messages].reverse().find((m) => m.role === "assistant");
  const lastUser = [...session.messages].reverse().find((m) => m.role === "user");

  return (
    <div className="live">
      {/* top bar */}
      <div className="live-top">
        <button className="btn btn-sm btn-ghost" onClick={exit} aria-label="Exit Live Talk">
          ← Exit
        </button>
        <div className="row" style={{ gap: 8 }}>
          <span className={cfg?.live ? "pill good" : "pill warn"}>
            {cfg?.live ? "Live" : "Mock"}
          </span>
          <button className="btn btn-sm btn-ghost" onClick={() => setShowSettings((s) => !s)}>
            Voice &amp; language
          </button>
        </div>
      </div>

      {/* settings drawer */}
      {showSettings && (
        <div className="card" style={{ margin: "12px auto 0", maxWidth: 640 }}>
          <div className="field">
            <label>Language</label>
            <select value={language || ""} onChange={(e) => setLanguage(e.target.value)}>
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
          </div>
          {character?.voice && (
            <p className="muted">
              Voice: {character.voice.speaker_id} · {character.voice.model} ·{" "}
              {character.voice.language_code}
              {character.voice.is_fallback && " (fallback in use)"}
            </p>
          )}
          <label className="switch">
            <input type="checkbox" checked={session.captions} onChange={(e) => session.setCaptions(e.target.checked)} />
            Show captions
          </label>
          <div style={{ height: 8 }} />
          <label className="switch">
            <input type="checkbox" checked={session.autoListen} onChange={(e) => session.setAutoListen(e.target.checked)} />
            Auto-listen after each reply
          </label>
          <div style={{ height: 8 }} />
          <label className="switch">
            <input type="checkbox" checked={pttMode} onChange={(e) => setPttMode(e.target.checked)} />
            Push-to-talk mode (hold to speak)
          </label>
        </div>
      )}

      {/* centre */}
      <div className="live-center">
        <div className="live-avatar-ring">
          {(listening || speaking) && <span className="ring" />}
          {character && (
            <Avatar characterId={character.id} avatarRef={character.avatar_ref} size={132} />
          )}
        </div>

        <div>
          <div className="live-name">{character?.display_name || "…"}</div>
          <div className="live-status">
            {session.state === "idle"
              ? "Ready to talk"
              : session.state === "speaking"
              ? "🔊 Speaking out loud..."
              : session.state === "listening"
              ? "🎙️ Listening to you... speak now"
              : session.state === "thinking"
              ? "✨ Thinking..."
              : session.state === "transcribing"
              ? "📝 Understanding your voice..."
              : statusLabel(session.state)}
          </div>
        </div>

        {session.state === "idle" && (
          <button
            className="btn btn-primary"
            style={{ fontSize: 16, padding: "12px 24px", borderRadius: 30, boxShadow: "0 0 25px rgba(255, 138, 91, 0.4)" }}
            onClick={() => void session.begin(true)}
          >
            🎙️ Start Live Voice Call
          </button>
        )}

        <Waveform level={session.level} active={listening || speaking} />

        <div className="live-meta">
          <span className="pill">{language || "en-IN"}</span>
          {character?.voice && <span className="pill">{character.voice.speaker_id}</span>}
          <span className="pill good">🔊 Speaker Active</span>
          {!session.autoListen && <span className="pill warn">push-to-talk</span>}
          {session.muted && <span className="pill bad">muted</span>}
        </div>

        {cfg && (
          <p className="muted" style={{ maxWidth: 520 }}>
            {cfg.note}
          </p>
        )}

        {session.error && <div className="notice bad" style={{ maxWidth: 560 }}>{session.error}</div>}
        {session.micPermission === "denied" && (
          <div className="notice warn" style={{ maxWidth: 560 }}>
            Microphone is blocked. Enable it in your browser, or switch on push-to-talk and
            allow access when prompted.
          </div>
        )}
        {crisis?.flagged && (
          <div className="notice warn" style={{ maxWidth: 560 }}>
            If things feel unbearable right now, please reach out to a real person or a helpline:
            {" "}
            {crisis.resources.map((r) => `${r.name} ${r.contact}`).join(" · ")}.
          </div>
        )}

        {/* captions */}
        {session.captions && (
          <div className="live-captions" aria-live="polite">
            {lastUser && <div className="cap user">{lastUser.content}</div>}
            {lastAssistant && <div className="cap">{lastAssistant.content}</div>}
          </div>
        )}
      </div>

      {/* transcript toggle */}
      {session.showTranscript && (
        <div className="live-captions" style={{ maxHeight: "22vh" }}>
          {session.messages.map((m) => (
            <div key={m.id} className={`cap ${m.role === "user" ? "user" : ""}`}>
              {m.content}
            </div>
          ))}
        </div>
      )}

      {/* controls */}
      <div className="live-controls">
        <button
          className={`ctrl ${session.muted ? "danger" : ""}`}
          onClick={session.toggleMute}
          title={session.muted ? "Unmute" : "Mute"}
          aria-label="Mute"
        >
          {session.muted ? "🔇" : "🔈"}
        </button>

        {pttMode ? (
          <button
            className={`ctrl primary ${listening ? "active" : ""}`}
            onMouseDown={() => void session.pushToTalkStart()}
            onMouseUp={() => void session.pushToTalkEnd()}
            onTouchStart={(e) => { e.preventDefault(); void session.pushToTalkStart(); }}
            onTouchEnd={(e) => { e.preventDefault(); void session.pushToTalkEnd(); }}
            aria-label="Hold to talk"
          >
            🎙
          </button>
        ) : (
          <button
            className={`ctrl primary ${listening ? "active" : ""}`}
            onClick={() => {
              if (speaking || busy) session.interrupt();
              if (listening) void session.stopAndSend();
              else void session.startListening();
            }}
            aria-label={listening ? "Stop and send" : "Start listening"}
          >
            {listening ? "⏹" : "🎙"}
          </button>
        )}

        <button
          className="ctrl"
          onClick={() => void session.replayLast()}
          title="Replay last reply"
          aria-label="Replay last reply"
        >
          ↺
        </button>

        <button
          className="ctrl"
          onClick={session.interrupt}
          title="Interrupt / stop audio"
          aria-label="Interrupt"
          disabled={!speaking && !busy}
        >
          ✋
        </button>

        <button
          className="ctrl"
          onClick={() => session.setShowTranscript((v) => !v)}
          title="Toggle transcript"
          aria-label="Toggle transcript"
        >
          ≡
        </button>

        <button className="ctrl danger" onClick={exit} title="Stop and exit" aria-label="Stop and exit">
          ✕
        </button>
      </div>

      {!session.autoListen && (
        <p className="muted" style={{ textAlign: "center" }}>
          Hold the mic button (or the space bar) while you speak, then release.
        </p>
      )}
      <div style={{ textAlign: "center" }}>
        <Link className="btn btn-sm btn-ghost" href={`/chat/${characterId}`}>Open text chat</Link>
      </div>
    </div>
  );
}
