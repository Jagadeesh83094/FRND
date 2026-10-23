"use client";

import { useRouter } from "next/navigation";
import type { Character } from "@/lib/types";

/**
 * Character switcher for the chat and Live Talk screens.
 *
 * Switching navigates to the new character's route. The voice session on the
 * old screen tears down on unmount (stopping playback and releasing the mic),
 * so identities never mix.
 */
export function CharacterSwitcher({
  characters,
  currentId,
  onBeforeSwitch,
}: {
  characters: Character[];
  currentId: string;
  onBeforeSwitch?: () => void;
}) {
  const router = useRouter();

  function change(id: string) {
    if (id === currentId) return;
    onBeforeSwitch?.(); // confirm / gracefully end the current voice session
    router.push(`/chat/${id}`);
  }

  return (
    <label className="row" style={{ gap: 8 }}>
      <span className="muted">Talking to</span>
      <select
        value={currentId}
        onChange={(e) => change(e.target.value)}
        aria-label="Switch character"
        style={{
          background: "var(--surface)",
          color: "var(--text)",
          border: "1px solid var(--border)",
          borderRadius: 10,
          padding: "8px 12px",
          font: "inherit",
        }}
      >
        {characters.map((c) => (
          <option key={c.id} value={c.id}>
            {c.display_name}
          </option>
        ))}
      </select>
    </label>
  );
}
