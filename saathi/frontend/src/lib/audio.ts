/** Browser audio helpers: microphone capture, level metering, playback, and WAV encoding. */

export function base64ToBlobUrl(base64: string, mime: string = "audio/wav"): string {
  try {
    const cleanBase64 = base64.includes(",") ? base64.split(",")[1] : base64;
    const binaryString = window.atob(cleanBase64.replace(/\s/g, ""));
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return URL.createObjectURL(new Blob([bytes], { type: mime || "audio/wav" }));
  } catch (err) {
    console.error("Failed to decode base64 audio", err);
    return "";
  }
}

/** Encode raw float PCM samples into standard 16-bit mono WAV */
export function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  function writeString(offset: number, str: string) {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  }

  // RIFF identifier
  writeString(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, "WAVE");

  // "fmt " chunk
  writeString(12, "fmt ");
  view.setUint32(16, 16, true); // SubChunk1Size (16 for PCM)
  view.setUint16(20, 1, true); // AudioFormat (1 for PCM)
  view.setUint16(22, 1, true); // NumChannels (1 mono)
  view.setUint32(24, sampleRate, true); // SampleRate
  view.setUint32(28, sampleRate * 2, true); // ByteRate (sampleRate * 1 * 16 / 8)
  view.setUint16(32, 2, true); // BlockAlign (1 * 16 / 8)
  view.setUint16(34, 16, true); // BitsPerSample (16 bits)

  // "data" chunk
  writeString(36, "data");
  view.setUint32(40, samples.length * 2, true);

  // Write 16-bit PCM samples
  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }

  return new Blob([view], { type: "audio/wav" });
}

export type LevelHandler = (level: number) => void;

export class MicRecorder {
  private stream: MediaStream | null = null;
  private recorder: MediaRecorder | null = null;
  private chunks: BlobPart[] = [];
  private analyser: AnalyserNode | null = null;
  private ctx: AudioContext | null = null;
  private processor: ScriptProcessorNode | null = null;
  private pcmBuffers: Float32Array[] = [];
  private pcmLength: number = 0;
  private raf: number | null = null;
  private onLevel?: LevelHandler;
  private _isRecording: boolean = false;

  /** Request the microphone and begin recording. Throws on denial. */
  async start(onLevel?: LevelHandler): Promise<void> {
    this.release();
    this.onLevel = onLevel;
    this.pcmBuffers = [];
    this.pcmLength = 0;

    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    this.ctx = new AudioContextClass();
    if (this.ctx.state === "suspended") {
      await this.ctx.resume();
    }

    const src = this.ctx.createMediaStreamSource(this.stream);
    this.analyser = this.ctx.createAnalyser();
    this.analyser.fftSize = 512;
    src.connect(this.analyser);

    // Audio sampling via ScriptProcessor to guarantee clean 16-bit WAV output
    const bufferSize = 4096;
    this.processor = this.ctx.createScriptProcessor(bufferSize, 1, 1);
    this.processor.onaudioprocess = (e) => {
      if (!this._isRecording) return;
      const input = e.inputBuffer.getChannelData(0);
      const copy = new Float32Array(input.length);
      copy.set(input);
      this.pcmBuffers.push(copy);
      this.pcmLength += copy.length;
    };
    src.connect(this.processor);
    this.processor.connect(this.ctx.destination);

    // MediaRecorder as backup
    try {
      const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "";
      this.chunks = [];
      this.recorder = new MediaRecorder(this.stream, mime ? { mimeType: mime } : undefined);
      this.recorder.ondataavailable = (e) => {
        if (e.data.size > 0) this.chunks.push(e.data);
      };
      this.recorder.start();
    } catch {
      // MediaRecorder unavailable, PCM handles it
    }

    this._isRecording = true;
    this._tick();
  }

  private _tick = () => {
    if (!this.analyser || !this.onLevel || !this._isRecording) return;
    const data = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteFrequencyData(data);
    let sum = 0;
    for (let i = 0; i < data.length; i++) sum += data[i];
    const level = Math.min(1, sum / data.length / 90);
    this.onLevel(level);
    this.raf = requestAnimationFrame(this._tick);
  };

  /** Stop recording and return captured audio as a WAV Blob. */
  async stop(): Promise<Blob> {
    this._isRecording = false;
    if (this.raf !== null) cancelAnimationFrame(this.raf);
    this.raf = null;

    const sampleRate = this.ctx?.sampleRate || 16000;

    // Build PCM samples
    if (this.pcmBuffers.length > 0 && this.pcmLength > 0) {
      const flat = new Float32Array(this.pcmLength);
      let offset = 0;
      for (const buf of this.pcmBuffers) {
        flat.set(buf, offset);
        offset += buf.length;
      }
      this.release();
      return encodeWav(flat, sampleRate);
    }

    // Fallback to MediaRecorder Blob
    return new Promise((resolve) => {
      const rec = this.recorder;
      if (!rec || rec.state === "inactive") {
        this.release();
        resolve(new Blob([], { type: "audio/wav" }));
        return;
      }
      rec.onstop = () => {
        const blob = new Blob(this.chunks, { type: "audio/webm" });
        this.release();
        resolve(blob);
      };
      rec.stop();
    });
  }

  /** Release microphone and audio graph. Safe to call repeatedly. */
  release(): void {
    this._isRecording = false;
    if (this.raf !== null) cancelAnimationFrame(this.raf);
    this.raf = null;
    try {
      if (this.recorder && this.recorder.state !== "inactive") {
        this.recorder.stop();
      }
    } catch {
      /* already stopped */
    }
    this.recorder = null;

    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }
    if (this.analyser) {
      this.analyser.disconnect();
      this.analyser = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }
    if (this.ctx) {
      this.ctx.close().catch(() => {});
      this.ctx = null;
    }
    this.pcmBuffers = [];
    this.pcmLength = 0;
    this.onLevel?.(0);
  }

  get isRecording(): boolean {
    return this._isRecording;
  }
}

export class AudioPlayer {
  private el: HTMLAudioElement | null = null;
  private url: string | null = null;
  private isBrowserSpeaking: boolean = false;

  async play(base64: string, mime: string = "audio/wav"): Promise<void> {
    this.stop();
    if (!base64 || !base64.trim()) return;

    const url = base64ToBlobUrl(base64, mime || "audio/wav");
    if (!url) return;
    this.url = url;
    const el = new Audio(url);
    this.el = el;

    return new Promise((resolve, reject) => {
      el.onended = () => {
        this.revoke();
        resolve();
      };
      el.onerror = () => {
        this.revoke();
        reject(new Error("playback failed"));
      };
      el.play().catch((err) => {
        this.revoke();
        reject(err);
      });
    });
  }

  /** Play text using browser speech synthesis */
  async speakText(text: string, languageCode: string = "en-IN"): Promise<void> {
    this.stop();
    if (!text || typeof window === "undefined" || !("speechSynthesis" in window)) return;

    return new Promise((resolve) => {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = languageCode;
      utterance.rate = 1.0;
      this.isBrowserSpeaking = true;
      utterance.onend = () => {
        this.isBrowserSpeaking = false;
        resolve();
      };
      utterance.onerror = () => {
        this.isBrowserSpeaking = false;
        resolve();
      };
      window.speechSynthesis.speak(utterance);
    });
  }

  /** Immediately stop playback so no audio is heard. */
  stop(): void {
    if (this.el) {
      this.el.onended = null;
      this.el.onerror = null;
      this.el.pause();
      this.el.currentTime = 0;
      this.el = null;
    }
    this.revoke();
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      this.isBrowserSpeaking = false;
    }
  }

  private revoke(): void {
    if (this.url) {
      URL.revokeObjectURL(this.url);
      this.url = null;
    }
  }

  get isPlaying(): boolean {
    return (!!this.el && !this.el.paused) || this.isBrowserSpeaking;
  }
}

export const globalAudioPlayer = new AudioPlayer();
