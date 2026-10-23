export type ResponseLength = "short" | "medium" | "long";

export interface VoiceConfig {
  provider: string;
  model: string;
  speaker_id: string;
  language_code: string;
  pace: number;
  fallback_speaker?: string | null;
  config_version: number;
  is_fallback: boolean;
  fallback_reason?: string | null;
}

export interface Character {
  id: string;
  definition_id?: string | null;
  user_character_id?: number | null;
  is_custom: boolean;
  display_name: string;
  nickname?: string | null;
  name_variants: Record<string, string[]>;
  avatar_ref: string;
  short_description: string;
  personality_description: string;
  conversational_style: string;
  languages: string[];
  language_prefs: string[];
  example_greeting: string;
  response_length: ResponseLength;
  behaviors: string[];
  voice?: VoiceConfig | null;
  customized: boolean;
}

export interface Message {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  language?: string | null;
  created_at: string;
  meta?: Record<string, unknown>;
}

export interface CharacterSession {
  character: Character;
  conversation_id: number;
  messages: Message[];
  memory_count: number;
  memories: Memory[];
}

export interface CrisisInfo {
  flagged: boolean;
  resources: { name: string; contact: string }[];
}

export interface ChatTurn {
  reply: string;
  message_id: number;
  conversation_id: number;
  character_id: string;
  character_name: string;
  language?: string | null;
  crisis: CrisisInfo;
  memories_used: string[];
  audio_base64?: string | null;
  audio_mime?: string | null;
  voice?: VoiceConfig | null;
  provider: string;
  latency_ms?: number | null;
}

export interface Memory {
  id: number;
  content: string;
  category: string;
  sensitivity: "normal" | "sensitive" | "intimate";
  origin_user_character_id?: number | null;
  origin_character_name?: string | null;
  shared_with: number[];
  shared_with_names: string[];
  created_at: string;
}

export interface VoiceCatalogEntry {
  id: string;
  speaker: string;
  language: string;
  style: string;
}

export interface VoiceConfigInfo {
  provider: string;
  live: boolean;
  chat_model: string;
  stt_model: string;
  tts_model: string;
  note: string;
}

export type TalkState =
  | "idle"
  | "listening"
  | "transcribing"
  | "thinking"
  | "speaking"
  | "interrupted"
  | "error";
