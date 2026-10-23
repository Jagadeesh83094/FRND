"use client";

import type { TalkState } from "@/lib/types";

const BARS = 22;

export function Waveform({ level, active }: { level: number; active: boolean }) {
  const base = active ? Math.max(0.08, level) : 0.06;
  return (
    <div className="wave" aria-hidden>
      {Array.from({ length: BARS }).map((_, i) => {
        // a gentle travelling wave so it always looks alive while listening
        const phase = (i / BARS) * Math.PI * 2;
        const wobble = active ? 0.5 + 0.5 * Math.sin(phase + level * 8) : 0.25;
        const h = 8 + base * 46 * (0.4 + wobble);
        return <span key={i} style={{ height: `${h}px`, opacity: active ? 0.95 : 0.4 }} />;
      })}
    </div>
  );
}

const LABELS: Record<TalkState, string> = {
  idle: "Ready",
  listening: "Listening…",
  transcribing: "Transcribing…",
  thinking: "Thinking…",
  speaking: "Speaking",
  interrupted: "Interrupted",
  error: "Something went wrong",
};

export function statusLabel(state: TalkState): string {
  return LABELS[state];
}

export function StatePill({ state }: { state: TalkState }) {
  const cls =
    state === "error" ? "pill bad" : state === "speaking" ? "pill good" : state === "listening" ? "pill warn" : "pill";
  return (
    <span className={cls} aria-live="polite">
      {LABELS[state]}
    </span>
  );
}
