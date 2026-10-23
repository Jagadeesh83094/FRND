"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Character, Memory } from "@/lib/types";

export default function MemoriesPage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [content, setContent] = useState("");
  const [category, setCategory] = useState("general");
  const [sensitivity, setSensitivity] = useState("normal");
  const [originId, setOriginId] = useState<number | "">("");
  const [shareWith, setShareWith] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [m, c] = await Promise.all([api.memories(), api.listCharacters()]);
      setMemories(m);
      setCharacters(c.filter((x) => x.user_character_id));
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function add() {
    if (!content.trim()) return;
    setError(null);
    try {
      if (originId) {
        // character-specific memory
        const res = await fetch(
          `${api.apiBase}/api/memories/for-character/${characters.find((c) => c.user_character_id === originId)?.id}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-User-Email": process.env.NEXT_PUBLIC_USER_EMAIL || "demo@saathi.app" },
            body: JSON.stringify({ content, category, sensitivity, share_with: shareWith }),
          }
        );
        if (!res.ok) throw new Error((await res.json())?.detail || "Failed");
      } else {
        await api.createMemory({ content, category, sensitivity, share_with: shareWith });
      }
      setContent("");
      setShareWith([]);
      setNotice("Memory saved.");
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function toggleShare(mem: Memory, ucId: number) {
    if (mem.shared_with.includes(ucId)) await api.revokeMemory(mem.id, ucId);
    else await api.grantMemory(mem.id, ucId);
    await load();
  }

  async function remove(id: number) {
    if (!confirm("Delete this memory?")) return;
    await api.deleteMemory(id);
    await load();
  }

  async function wipe() {
    if (!confirm("Delete ALL your data — every character, conversation and memory? This cannot be undone.")) return;
    await api.deleteAllData();
    await load();
    setNotice("All user data deleted.");
  }

  return (
    <main style={{ maxWidth: 820 }}>
      <h1>Memories</h1>
      <p className="sub">
        A memory belongs only to the character it came from, unless you explicitly share it.
        Intimate details are never shared automatically.
      </p>

      {error && <div className="notice bad" style={{ marginBottom: 14 }}>{error}</div>}
      {notice && <div className="notice" style={{ marginBottom: 14 }}>{notice}</div>}

      <div className="card" style={{ marginBottom: 24 }}>
        <h2>Add a memory</h2>
        <div className="field">
          <label>What should be remembered?</label>
          <input value={content} onChange={(e) => setContent(e.target.value)} placeholder="e.g. Placement interview on Friday" />
        </div>
        <div className="row" style={{ gap: 12 }}>
          <div className="field" style={{ flex: 1 }}>
            <label>Belongs to</label>
            <select value={originId} onChange={(e) => setOriginId(e.target.value ? Number(e.target.value) : "")}>
              <option value="">Shared (no single owner)</option>
              {characters.map((c) => (
                <option key={c.user_character_id} value={c.user_character_id!}>
                  {c.display_name}
                </option>
              ))}
            </select>
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>Category</label>
            <input value={category} onChange={(e) => setCategory(e.target.value)} />
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>Sensitivity</label>
            <select value={sensitivity} onChange={(e) => setSensitivity(e.target.value)}>
              <option value="normal">Normal</option>
              <option value="sensitive">Sensitive</option>
              <option value="intimate">Intimate (never auto-shared)</option>
            </select>
          </div>
        </div>
        <div className="field">
          <label>Share with these characters</label>
          <div className="row" style={{ gap: 10 }}>
            {characters.map((c) => (
              <label key={c.user_character_id} className="switch">
                <input
                  type="checkbox"
                  checked={shareWith.includes(c.user_character_id!)}
                  onChange={() =>
                    setShareWith((prev) =>
                      prev.includes(c.user_character_id!)
                        ? prev.filter((x) => x !== c.user_character_id)
                        : [...prev, c.user_character_id!]
                    )
                  }
                />
                {c.display_name}
              </label>
            ))}
          </div>
        </div>
        <button className="btn-primary" onClick={() => void add()}>Save memory</button>
      </div>

      <h2 className="section-title">Your memories ({memories.length})</h2>
      <div className="stack">
        {memories.length === 0 && <p className="muted">Nothing saved yet.</p>}
        {memories.map((m) => (
          <div key={m.id} className="card">
            <div className="spread">
              <div>
                <div style={{ fontWeight: 600 }}>{m.content}</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {m.origin_character_name ? `From ${m.origin_character_name}` : "Shared"} ·{" "}
                  {m.category} · {m.sensitivity}
                </div>
              </div>
              <button className="btn btn-sm btn-danger" onClick={() => void remove(m.id)}>Delete</button>
            </div>
            <hr className="sep" />
            <div className="muted" style={{ marginBottom: 8 }}>
              Who can use this memory
            </div>
            <div className="row" style={{ gap: 10 }}>
              {characters.map((c) => {
                const shared = m.shared_with.includes(c.user_character_id!);
                const isOrigin = m.origin_user_character_id === c.user_character_id;
                return (
                  <label key={c.user_character_id} className="switch" title={isOrigin ? "Owner" : ""}>
                    <input
                      type="checkbox"
                      checked={shared || isOrigin}
                      disabled={isOrigin}
                      onChange={() => void toggleShare(m, c.user_character_id!)}
                    />
                    {c.display_name}
                    {isOrigin ? " (owner)" : ""}
                  </label>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <hr className="sep" />
      <h2 className="section-title">Danger zone</h2>
      <button className="btn-danger" onClick={() => void wipe()}>
        Delete all my data
      </button>
    </main>
  );
}
