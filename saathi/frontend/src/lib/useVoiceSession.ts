"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { AudioPlayer, MicRecorder } from "./audio";
import type { Message, TalkState } from "./types";

export type MicPermission = "unknown" | "granted" | "denied";

interface Options {
  characterId: string;
  language?: string;
  onTurn?: (turn: { user?: string; assistant?: string; crisis: boolean }) => void;
}

const SILENCE_MS = 1400;      // end-of-speech window for auto detection
const SILENCE_LEVEL = 0.06;   // below this counts as silence
const MIN_SPEECH_MS = 350;    // ignore taps that are too short

/**
 * The Live Talk conversation state machine.
 *
 * idle -> listening -> transcribing -> thinking -> speaking -> (listening | idle)
 * with `interrupted` and `error` as first-class states. A monotonically
 * increasing turn id discards stale responses so out-of-order or duplicate
 * audio can never play.
 */
export function useVoiceSession({ characterId, language, onTurn }: Options) {
  const [state, setState] = useState<TalkState>("idle");
  const [level, setLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [micPermission, setMicPermission] = useState<MicPermission>("unknown");
  const [autoListen, setAutoListen] = useState(true);
  const [captions, setCaptions] = useState(true);
  const [showTranscript, setShowTranscript] = useState(true);
  const [muted, setMuted] = useState(false);
  const [live, setLive] = useState<boolean | null>(null);

  const recorderRef = useRef<MicRecorder | null>(null);
  const playerRef = useRef<AudioPlayer | null>(null);
  const turnIdRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const lastAssistantRef = useRef<{ text: string; audio?: string; mime?: string } | null>(null);
  const speechStartRef = useRef<number>(0);
  const silenceSinceRef = useRef<number>(0);
  const stoppedRef = useRef(false);
  const stateRef = useRef<TalkState>("idle");
  stateRef.current = state;

  // Local message helpers --------------------------------------------------- //
  const pushMessage = useCallback((role: Message["role"], content: string) => {
    setMessages((m) => [
      ...m,
      { id: Date.now() + Math.random(), role, content, created_at: new Date().toISOString() },
    ]);
  }, []);

  // Setup / teardown -------------------------------------------------------- //
  useEffect(() => {
    recorderRef.current = new MicRecorder();
    playerRef.current = new AudioPlayer();
    api
      .voiceConfig()
      .then((c) => setLive(c.live))
      .catch(() => setLive(null));
    return () => {
      stoppedRef.current = true;
      turnIdRef.current++;
      abortRef.current?.abort();
      recorderRef.current?.release();
      playerRef.current?.stop();
    };
  }, [characterId]);

  // ---- core: send a turn -------------------------------------------------- //
  const runTurn = useCallback(
    async (text: string, opts?: { fromVoice?: boolean }) => {
      const clean = text.trim();
      if (!clean) {
        setState("idle");
        return;
      }
      const myTurn = ++turnIdRef.current;
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      pushMessage("user", clean);
      setState("thinking");
      setError(null);

      try {
        const turn = await api.chat(
          characterId,
          { text: clean, mode: opts?.fromVoice ? "voice" : "text", language, speak: true },
          { signal: ctrl.signal }
        );
        if (myTurn !== turnIdRef.current) return; // superseded -> drop

        pushMessage("assistant", turn.reply);
        lastAssistantRef.current = {
          text: turn.reply,
          audio: turn.audio_base64 || undefined,
          mime: turn.audio_mime || undefined,
        };
        onTurn?.({ user: clean, assistant: turn.reply, crisis: turn.crisis.flagged });

        if (turn.audio_base64) {
          setState("speaking");
          try {
            await playerRef.current!.play(turn.audio_base64, turn.audio_mime || "audio/wav");
          } catch (playbackErr) {
            console.warn("Audio playback failed, falling back to speech synthesis", playbackErr);
            await playerRef.current!.speakText(turn.reply, language || "en-IN");
          }
          if (myTurn !== turnIdRef.current) return;
        } else {
          // If no audio was returned by provider, use browser speech synthesis so speaker always speaks!
          setState("speaking");
          try {
            await playerRef.current!.speakText(turn.reply, language || "en-IN");
          } catch {
            /* ignore */
          }
          if (myTurn !== turnIdRef.current) return;
        }
        if (stoppedRef.current || myTurn !== turnIdRef.current) return;
        if (autoListen && !muted) {
          void startListening();
        } else {
          setState("idle");
        }
      } catch (e: unknown) {
        if (myTurn !== turnIdRef.current) return;
        if ((e as { name?: string })?.name === "AbortError") return;
        setError((e as Error).message || "Something went wrong.");
        setState("error");
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [characterId, language, autoListen, muted, onTurn, pushMessage]
  );

  // ---- listening ---------------------------------------------------------- //
  const startListening = useCallback(async () => {
    if (recorderRef.current?.isRecording) return;
    setError(null);
    try {
      await recorderRef.current!.start((lvl) => {
        setLevel(lvl);
        // simple energy-based end-of-speech detection for auto mode
        if (!autoListen) return;
        const now = performance.now();
        if (lvl > SILENCE_LEVEL) {
          if (!speechStartRef.current) speechStartRef.current = now;
          silenceSinceRef.current = 0;
        } else if (speechStartRef.current) {
          if (!silenceSinceRef.current) silenceSinceRef.current = now;
          const spokeFor = now - speechStartRef.current;
          const silentFor = now - silenceSinceRef.current;
          if (spokeFor > MIN_SPEECH_MS && silentFor > SILENCE_MS) {
            speechStartRef.current = 0;
            silenceSinceRef.current = 0;
            void stopAndSend();
          }
        }
      });
      setMicPermission("granted");
      setState("listening");
    } catch (e: unknown) {
      const name = (e as { name?: string })?.name;
      if (name === "NotAllowedError" || name === "SecurityError") {
        setMicPermission("denied");
        setError(
          "Microphone access is blocked. Allow it in your browser settings, or use push-to-talk."
        );
      } else {
        setError("Couldn't start the microphone. Try push-to-talk instead.");
      }
      setState("error");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoListen]);

  const stopAndSend = useCallback(async () => {
    const rec = recorderRef.current;
    if (!rec?.isRecording) return;
    setState("transcribing");
    const blob = await rec.stop();
    setLevel(0);
    if (!blob || blob.size < 1200) {
      // too short to be speech
      setState(autoListen ? "listening" : "idle");
      if (autoListen) void startListening();
      return;
    }
    const myTurn = turnIdRef.current; // transcription belongs to current turn
    try {
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      const res = await api.transcribe(blob, language || "en-IN", { signal: ctrl.signal });
      if (myTurn !== turnIdRef.current) return;
      if (!res.text.trim()) {
        setState(autoListen ? "listening" : "idle");
        if (autoListen) void startListening();
        return;
      }
      await runTurn(res.text, { fromVoice: true });
    } catch (e: unknown) {
      if ((e as { name?: string })?.name === "AbortError") return;
      setError((e as Error).message || "Couldn't transcribe that.");
      setState("error");
    }
  }, [autoListen, language, runTurn, startListening]);

  // ---- interruption ------------------------------------------------------- //
  const interrupt = useCallback(() => {
    turnIdRef.current++; // invalidate any in-flight response
    abortRef.current?.abort();
    playerRef.current?.stop(); // no stale audio
    setLevel(0);
    setState("interrupted");
  }, []);

  // ---- public actions ----------------------------------------------------- //
  const begin = useCallback(async (shouldGreet = false) => {
    stoppedRef.current = false;
    if (shouldGreet) {
      try {
        setState("thinking");
        const g = await api.greeting(characterId, true);
        pushMessage("assistant", g.reply);
        lastAssistantRef.current = {
          text: g.reply,
          audio: g.audio_base64 || undefined,
          mime: g.audio_mime || undefined,
        };
        setState("speaking");
        if (g.audio_base64) {
          try {
            await playerRef.current!.play(g.audio_base64, g.audio_mime || "audio/wav");
          } catch {
            await playerRef.current!.speakText(g.reply, language || "en-IN");
          }
        } else {
          await playerRef.current!.speakText(g.reply, language || "en-IN");
        }
      } catch (err) {
        console.warn("Greeting failed", err);
      }
    }
    await startListening();
  }, [characterId, language, pushMessage, startListening]);

  const end = useCallback(() => {
    turnIdRef.current++;
    abortRef.current?.abort();
    playerRef.current?.stop();
    recorderRef.current?.release();
    setLevel(0);
    setState("idle");
  }, []);

  const pushToTalkStart = useCallback(async () => {
    // Push-to-talk always starts a fresh recording, interrupting anything.
    if (stateRef.current === "speaking" || stateRef.current === "thinking") interrupt();
    await startListening();
  }, [interrupt, startListening]);

  const pushToTalkEnd = useCallback(async () => {
    await stopAndSend();
  }, [stopAndSend]);

  const replayLast = useCallback(async () => {
    const last = lastAssistantRef.current;
    if (!last?.text) {
      setError("No audio available to replay.");
      return;
    }
    const myTurn = turnIdRef.current;
    setState("speaking");
    try {
      if (last.audio) {
        await playerRef.current!.play(last.audio, last.mime || "audio/wav");
      } else {
        await playerRef.current!.speakText(last.text, language || "en-IN");
      }
    } catch {
      await playerRef.current!.speakText(last.text, language || "en-IN");
    }
    if (myTurn === turnIdRef.current) setState(autoListen ? "listening" : "idle");
  }, [autoListen, language]);

  const sendText = useCallback(
    async (text: string) => {
      if (stateRef.current === "speaking" || stateRef.current === "thinking") interrupt();
      await runTurn(text, { fromVoice: false });
    },
    [interrupt, runTurn]
  );

  const toggleMute = useCallback(() => {
    setMuted((m) => {
      const next = !m;
      if (next) {
        recorderRef.current?.release();
        playerRef.current?.stop();
        setState("idle");
      }
      return next;
    });
  }, []);

  return {
    state,
    level,
    error,
    messages,
    setMessages,
    micPermission,
    autoListen,
    setAutoListen,
    captions,
    setCaptions,
    showTranscript,
    setShowTranscript,
    muted,
    toggleMute,
    live,
    begin,
    end,
    startListening,
    stopAndSend,
    interrupt,
    pushToTalkStart,
    pushToTalkEnd,
    replayLast,
    sendText,
    pushMessage,
    clearError: () => setError(null),
  };
}
