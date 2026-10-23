"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://localhost:8000";
const USER_EMAIL = process.env.NEXT_PUBLIC_USER_EMAIL || "demo@saathi.app";

export default function OnboardingPage() {
  const [disclosure, setDisclosure] = useState("");
  const [done, setDone] = useState(false);
  const [ack, setAck] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/onboarding`, { headers: { "X-User-Email": USER_EMAIL } })
      .then((r) => r.json())
      .then((d) => {
        setDisclosure(d.ai_disclosure);
        setDone(d.onboarding_completed);
      })
      .catch(() => setError("Couldn't reach the backend."));
  }, []);

  async function submit() {
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/onboarding`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-User-Email": USER_EMAIL },
        body: JSON.stringify({ acknowledged_ai: ack, display_name: name || null }),
      });
      if (!res.ok) throw new Error("Failed");
      const d = await res.json();
      setDone(d.onboarding_completed);
    } catch {
      setError("Couldn't save that. Try again.");
    }
  }

  return (
    <main style={{ maxWidth: 680 }}>
      <h1>Before you start</h1>
      <p className="sub">{disclosure || "Loading…"}</p>

      <div className="card">
        <div className="checkline">
          <input
            type="checkbox"
            checked={ack}
            onChange={(e) => setAck(e.target.checked)}
            aria-label="Acknowledge AI disclosure"
          />
          <span>
            I understand that every character in Saathi is an AI-generated companion — not a real
            person, not my real family or friends, and not a substitute for professional care.
          </span>
        </div>

        <div className="field" style={{ marginTop: 16 }}>
          <label>What should we call you? (optional)</label>
          <input value={name} onChange={(e) => setName(e.target.value)} maxLength={120} />
        </div>

        {error && <div className="notice bad" style={{ marginBottom: 12 }}>{error}</div>}

        <button className="btn-primary" onClick={() => void submit()} disabled={!ack}>
          {done ? "Update" : "Continue"}
        </button>
        {done && <span className="pill good" style={{ marginLeft: 12 }}>Acknowledged</span>}
      </div>

      <hr className="sep" />
      <h2 className="section-title">If you're struggling</h2>
      <p className="muted">
        These characters can keep you company, but they can't replace real support. If you're in
        distress, please reach out to a person you trust or a helpline.
      </p>
      <div className="stack">
        <div className="notice">Tele-MANAS (Govt. of India, 24×7): <strong>14416</strong> or <strong>1-800-891-4416</strong></div>
        <div className="notice">KIRAN Mental Health Helpline: <strong>1800-599-0019</strong></div>
        <div className="notice">AASRA: <strong>+91-98204-66726</strong></div>
      </div>

      <p style={{ marginTop: 20 }}>
        <Link className="btn btn-sm" href="/">Back to characters</Link>
      </p>
    </main>
  );
}
