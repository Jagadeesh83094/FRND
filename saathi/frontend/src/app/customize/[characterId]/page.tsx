"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Character, VoiceCatalogEntry } from "@/lib/types";
import { Avatar } from "@/components/Avatar";
import { VoicePreviewButton } from "@/components/VoicePreviewButton";

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

const NAME_VARIANTS: Record<string, string[]> = {
  mom: ["Mom", "Amma", "Maa", "Mummy"],
  dad: ["Dad", "Nanna", "Papa", "Appa"],
  grandmother: ["Dadi", "Ammamma", "Nani", "Grandma"],
  grandfather: ["Dada", "Thatha", "Nana", "Grandpa"],
};

export default function CustomizePage() {
  const params = useParams<{ characterId: string }>();
  const router = useRouter();
  const characterId = params.characterId;
  const isNewCustom = characterId === "custom";

  const [character, setCharacter] = useState<Character | null>(null);
  const [voices, setVoices] = useState<VoiceCatalogEntry[]>([]);
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [displayName, setDisplayName] = useState("");
  const [nickname, setNickname] = useState("");
  const [personality, setPersonality] = useState("");
  const [style, setStyle] = useState("");
  const [langPrefs, setLangPrefs] = useState<string[]>(["en-IN"]);
  const [responseLength, setResponseLength] = useState("short");
  const [voiceId, setVoiceId] = useState("");

  const load = useCallback(async () => {
    try {
      const [c, v] = await Promise.all([api.getSession(characterId), api.voices()]);
      setCharacter(c.character);
      setVoices(v);
      setDisplayName(c.character.display_name);
      setNickname(c.character.nickname || "");
      setLangPrefs(c.character.language_prefs?.length ? c.character.language_prefs : ["en-IN"]);
      setResponseLength(c.character.response_length);
      if (!isNewCustom) {
        setPersonality(c.character.personality_description);
        setStyle(c.character.conversational_style);
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }, [characterId, isNewCustom]);

  useEffect(() => {
    void load();
  }, [load]);

  function toggleLang(code: string) {
    setLangPrefs((prev) =>
      prev.includes(code) ? prev.filter((l) => l !== code) : [...prev, code].slice(0, 3)
    );
  }

  async function save() {
    setError(null);
    setSaved(null);
    try {
      if (isNewCustom) {
        const created = await api.createCustomCharacter({
          display_name: displayName,
          nickname: nickname || null,
          personality,
          conversational_style: style,
          language: langPrefs[0] || "en-IN",
          voice_id: voiceId || null,
          response_length: responseLength,
        });
        router.push(`/chat/${created.id}`);
        return;
      }
      const overrides: Record<string, string> = {};
      if (personality) overrides.personality = personality;
      if (style) overrides.conversational_style = style;
      await api.updateCharacter(characterId, {
        display_name: displayName,
        nickname,
        language_prefs: langPrefs,
        response_length: responseLength,
        voice_id: voiceId || undefined,
        voice_language: voiceId ? langPrefs[0] : undefined,
        personality_overrides: Object.keys(overrides).length ? overrides : undefined,
      });
      setSaved("Saved.");
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function deleteHistory() {
    if (!confirm("Delete this character's conversation history and its private memories?")) return;
    await api.deleteCharacterHistory(characterId);
    setSaved("History deleted.");
  }

  const voiceOptions = voices.filter((v) => langPrefs.includes(v.language));

  return (
    <main style={{ maxWidth: 720 }}>
      <h1>{isNewCustom ? "Create a character" : `Edit ${character?.display_name || ""}`}</h1>
      <p className="sub">
        Shape how this character talks and sounds. Safety, privacy and honesty rules always
        apply and cannot be changed here.
      </p>

      <div className="row" style={{ marginBottom: 18 }}>
        <Avatar characterId={isNewCustom ? "custom" : characterId} avatarRef={character?.avatar_ref} size={54} />
        {!isNewCustom && <VoicePreviewButton characterId={characterId} label="Preview voice" />}
      </div>

      {error && <div className="notice bad" style={{ marginBottom: 14 }}>{error}</div>}
      {saved && <div className="notice" style={{ marginBottom: 14 }}>{saved}</div>}

      <div className="card">
        <div className="field">
          <label>Name</label>
          <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} maxLength={40} />
        </div>

        {NAME_VARIANTS[characterId] && (
          <div className="field">
            <label>Or pick a regional name</label>
            <div className="row" style={{ gap: 8 }}>
              {NAME_VARIANTS[characterId].map((n) => (
                <button key={n} className="btn btn-sm" type="button" onClick={() => setDisplayName(n)}>
                  {n}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="field">
          <label>Nickname (optional)</label>
          <input value={nickname} onChange={(e) => setNickname(e.target.value)} maxLength={40} />
        </div>

        <div className="field">
          <label>Languages (up to 3, first is primary)</label>
          <div className="row" style={{ gap: 10 }}>
            {LANGUAGES.map((l) => (
              <label key={l.code} className="switch">
                <input
                  type="checkbox"
                  checked={langPrefs.includes(l.code)}
                  onChange={() => toggleLang(l.code)}
                />
                {l.label}
              </label>
            ))}
          </div>
        </div>

        <div className="field">
          <label>Reply length</label>
          <select value={responseLength} onChange={(e) => setResponseLength(e.target.value)}>
            <option value="short">Short (best for voice)</option>
            <option value="medium">Medium</option>
            <option value="long">Longer</option>
          </select>
        </div>

        <div className="field">
          <label>Voice</label>
          <select value={voiceId} onChange={(e) => setVoiceId(e.target.value)}>
            <option value="">Default for the language</option>
            {voiceOptions.map((v) => (
              <option key={v.id} value={v.id}>
                {v.speaker} — {v.style} ({v.language})
              </option>
            ))}
          </select>
          <span className="muted">
            Only real, supported Sarvam voices are listed. If a voice isn't available for a
            language, a compatible fallback is used automatically.
          </span>
        </div>

        {isNewCustom && (
          <>
            <div className="field">
              <label>Personality</label>
              <textarea rows={3} value={personality} onChange={(e) => setPersonality(e.target.value)} />
            </div>
            <div className="field">
              <label>Conversational style</label>
              <textarea rows={2} value={style} onChange={(e) => setStyle(e.target.value)} />
            </div>
          </>
        )}

        {!isNewCustom && (
          <>
            <div className="field">
              <label>Personality (override)</label>
              <textarea rows={3} value={personality} onChange={(e) => setPersonality(e.target.value)} />
            </div>
            <div className="field">
              <label>Conversational style (override)</label>
              <textarea rows={2} value={style} onChange={(e) => setStyle(e.target.value)} />
            </div>
          </>
        )}

        <div className="row" style={{ gap: 10 }}>
          <button className="btn-primary" onClick={() => void save()}>
            {isNewCustom ? "Create character" : "Save changes"}
          </button>
          {!isNewCustom && (
            <button className="btn-danger" onClick={() => void deleteHistory()}>
              Delete this character's history
            </button>
          )}
        </div>
      </div>
    </main>
  );
}
