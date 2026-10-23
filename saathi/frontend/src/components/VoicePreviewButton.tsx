"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { AudioPlayer } from "@/lib/audio";

export function VoicePreviewButton({
  characterId,
  label = "Hear voice",
  className = "btn btn-sm",
}: {
  characterId: string;
  label?: string;
  className?: string;
}) {
  const [state, setState] = useState<"idle" | "loading" | "playing" | "error">("idle");
  const [note, setNote] = useState<string | null>(null);

  async function play() {
    setState("loading");
    setNote(null);
    try {
      const res = await api.voicePreview(characterId);
      const player = new AudioPlayer();
      setState("playing");
      if (res.is_fallback) {
        setNote(`Using a compatible fallback voice (${res.fallback_reason || "unavailable"}).`);
      }
      await player.play(res.audio_base64, res.mime_type);
      setState("idle");
    } catch (e) {
      setState("error");
      setNote((e as Error).message || "Couldn't play a sample.");
    }
  }

  return (
    <span className="row" style={{ gap: 8 }}>
      <button className={className} onClick={play} disabled={state === "loading" || state === "playing"}>
        {state === "loading" ? "Loading…" : state === "playing" ? "Playing…" : label}
      </button>
      {note && <span className="muted">{note}</span>}
    </span>
  );
}
