"use client";

import Link from "next/link";
import type { Character } from "@/lib/types";
import { Avatar } from "./Avatar";
import { VoicePreviewButton } from "./VoicePreviewButton";

export function CharacterCard({ character }: { character: Character }) {
  const voice = character.voice;
  const langs = (character.language_prefs?.length ? character.language_prefs : character.languages) || [];
  return (
    <div className="card">
      <div className="spread">
        <Avatar characterId={character.id} avatarRef={character.avatar_ref} size={58} />
        <div className="row" style={{ gap: 6 }}>
          {character.is_custom && <span className="tag">Custom</span>}
          {character.customized && <span className="tag">Personalised</span>}
        </div>
      </div>

      <h3>{character.display_name}</h3>
      <p>{character.short_description}</p>

      <div className="row" style={{ gap: 6, marginBottom: 14 }}>
        {langs.slice(0, 3).map((l) => (
          <span key={l} className="tag">{l}</span>
        ))}
        {voice && (
          <span className="tag" title={`${voice.model} · ${voice.speaker_id}`}>
            {voice.is_fallback ? "fallback voice" : voice.speaker_id}
          </span>
        )}
      </div>

      <div className="row" style={{ gap: 8 }}>
        <Link className="btn btn-sm btn-primary" href={`/chat/${character.id}`}>Chat</Link>
        <Link className="btn btn-sm" href={`/live/${character.id}`}>Live Talk</Link>
        <Link className="btn btn-sm btn-ghost" href={`/customize/${character.id}`}>Edit</Link>
      </div>
      <div style={{ marginTop: 12 }}>
        <VoicePreviewButton characterId={character.id} />
      </div>
    </div>
  );
}
