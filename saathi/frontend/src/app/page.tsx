"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Character, VoiceConfigInfo } from "@/lib/types";
import { CharacterCard } from "@/components/CharacterCard";

export default function HomePage() {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [cfg, setCfg] = useState<VoiceConfigInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.listCharacters(), api.voiceConfig()])
      .then(([chars, info]) => {
        setCharacters(chars);
        setCfg(info);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main>
      <h1>Who do you want to talk to?</h1>
      <p className="sub">
        Pick a companion and talk out loud or by text. Each one has its own personality,
        its own voice, and its own private conversation with you.
      </p>

      <div className="notice warn" role="note" style={{ marginBottom: 22 }}>
        <strong>Everyone here is AI.</strong> These are fictional companions, not your real
        family or friends, and they have no real memories. They can keep you company and help
        you think — but they are not a replacement for the people in your life or for
        professional care.{" "}
        <Link href="/onboarding" style={{ textDecoration: "underline" }}>Learn more</Link>
      </div>

      {cfg && (
        <div className="row" style={{ marginBottom: 18, gap: 8 }}>
          <span className={cfg.live ? "pill good" : "pill warn"}>
            {cfg.live ? "Live Sarvam models" : "Offline mock mode"}
          </span>
          <span className="pill">{cfg.chat_model}</span>
          <span className="pill">{cfg.tts_model}</span>
          <span className="pill">{cfg.stt_model}</span>
        </div>
      )}

      {loading && <p className="muted">Loading characters…</p>}
      {error && <div className="notice bad">{error} — is the backend running on port 8000?</div>}

      <div className="grid">
        {characters.map((c) => (
          <CharacterCard key={c.id} character={c} />
        ))}
      </div>

      <h2 className="section-title">Make your own</h2>
      <div className="card" style={{ maxWidth: 520 }}>
        <h3>Custom character</h3>
        <p>
          Define a name, personality, tone, language and voice. Safety, privacy and honesty
          rules always apply and can't be switched off.
        </p>
        <Link className="btn btn-sm btn-primary" href="/customize/custom">Create a character</Link>
      </div>
    </main>
  );
}
