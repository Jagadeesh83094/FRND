import type {
  Character,
  CharacterSession,
  ChatTurn,
  Memory,
  Message,
  VoiceCatalogEntry,
  VoiceConfigInfo,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://localhost:8000";
const DEV_USER_EMAIL = process.env.NEXT_PUBLIC_USER_EMAIL || "demo@saathi.app";
const TOKEN_KEY = "saathi_access_token";

export function saveAccessToken(token: string) {
  if (typeof window !== "undefined") window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearAccessToken() {
  if (typeof window !== "undefined") window.localStorage.removeItem(TOKEN_KEY);
}

export function hasAccessToken(): boolean {
  return typeof window !== "undefined" && Boolean(window.localStorage.getItem(TOKEN_KEY));
}

class ApiError extends Error {
  status: number;
  kind?: string;
  constructor(message: string, status: number, kind?: string) {
    super(message);
    this.status = status;
    this.kind = kind;
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        ...(typeof window !== "undefined" && window.localStorage.getItem(TOKEN_KEY)
          ? { Authorization: `Bearer ${window.localStorage.getItem(TOKEN_KEY)}` }
          : { "X-User-Email": DEV_USER_EMAIL }),
        ...(init?.body && !(init.body instanceof FormData)
          ? { "Content-Type": "application/json" }
          : {}),
        ...(init?.headers || {}),
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError("Can't reach the Saathi backend. Is it running?", 0, "network");
  }
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail ?? body;
    } catch {
      /* ignore */
    }
    const message =
      typeof detail === "string"
        ? detail
        : (detail as { message?: string })?.message || "Something went wrong";
    const kind = (detail as { kind?: string })?.kind;
    throw new ApiError(message, res.status, kind);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  apiBase: API_BASE,

  register: (body: { email: string; password: string; display_name?: string }) =>
    req<{ access_token: string; token_type: string; expires_in: number; user_id: number; email: string; display_name: string }>("/api/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body: { email: string; password: string }) =>
    req<{ access_token: string; token_type: string; expires_in: number; user_id: number; email: string; display_name: string }>("/api/auth/login", { method: "POST", body: JSON.stringify(body) }),

  voiceConfig: () => req<VoiceConfigInfo>("/api/voice/config"),

  listCharacters: () => req<Character[]>("/api/characters"),
  getSession: (characterId: string) =>
    req<CharacterSession>(`/api/characters/${characterId}/session`),

  greeting: (characterId: string, speak = false) =>
    req<ChatTurn>(`/api/characters/${characterId}/greeting?speak=${speak}`, {
      method: "POST",
    }),

  chat: (
    characterId: string,
    body: { text: string; mode?: "text" | "voice"; language?: string; speak?: boolean },
    opts?: { signal?: AbortSignal }
  ) =>
    req<ChatTurn>(`/api/characters/${characterId}/chat`, {
      method: "POST",
      body: JSON.stringify(body),
      signal: opts?.signal,
    }),

  updateCharacter: (characterId: string, body: Record<string, unknown>) =>
    req<Character>(`/api/characters/${characterId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  createCustomCharacter: (body: Record<string, unknown>) =>
    req<Character>("/api/characters/custom", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  deleteCharacterHistory: (characterId: string) =>
    req<{ conversations_deleted: number; memories_deleted: number }>(
      `/api/characters/${characterId}/history`,
      { method: "DELETE" }
    ),

  voices: () => req<VoiceCatalogEntry[]>("/api/voices"),

  messages: (conversationId: number) =>
    req<Message[]>(`/api/conversations/${conversationId}/messages`),

  memories: () => req<Memory[]>("/api/memories"),
  createMemory: (body: {
    content: string;
    category?: string;
    sensitivity?: string;
    share_with?: number[];
  }) => req<Memory>("/api/memories", { method: "POST", body: JSON.stringify(body) }),
  grantMemory: (memory_id: number, user_character_id: number) =>
    req<Memory>("/api/memories/grant", {
      method: "POST",
      body: JSON.stringify({ memory_id, user_character_id }),
    }),
  revokeMemory: (memory_id: number, user_character_id: number) =>
    req<Memory>("/api/memories/revoke", {
      method: "POST",
      body: JSON.stringify({ memory_id, user_character_id }),
    }),
  deleteMemory: (memoryId: number) =>
    req<{ deleted: number }>(`/api/memories/${memoryId}`, { method: "DELETE" }),
  deleteAllData: () =>
    req<{ characters_deleted: number }>("/api/user/data", { method: "DELETE" }),

  transcribe: async (blob: Blob, language: string, opts?: { signal?: AbortSignal }) => {
    const fd = new FormData();
    const filename = blob.type.includes("wav") ? "clip.wav" : "clip.webm";
    fd.append("file", blob, filename);
    fd.append("language", language);
    fd.append("mode", "transcribe");
    return req<{ text: string; language_code: string | null; provider: string }>(
      "/api/voice/transcribe",
      { method: "POST", body: fd, signal: opts?.signal }
    );
  },

  tts: (characterId: string, text: string, language?: string) =>
    req<{
      audio_base64: string;
      mime_type: string;
      speaker_id: string;
      provider: string;
    }>(`/api/characters/${characterId}/tts`, {
      method: "POST",
      body: JSON.stringify({ text, language }),
    }),

  voicePreview: (characterId: string) =>
    req<{
      audio_base64: string;
      mime_type: string;
      speaker_id: string;
      is_fallback: boolean;
      fallback_reason?: string | null;
    }>(`/api/characters/${characterId}/voice-preview`),
};

export { ApiError };
