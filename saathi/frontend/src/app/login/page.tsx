"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, saveAccessToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = mode === "login"
        ? await api.login({ email, password })
        : await api.register({ email, password, display_name: displayName || undefined });
      saveAccessToken(result.access_token);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ maxWidth: 480, margin: "32px auto" }}>
      <h1>{mode === "login" ? "Welcome back" : "Create your Saathi account"}</h1>
      <p className="sub">
        Sign in to keep your conversations and memories linked to your own account.
      </p>
      <div className="card">
        <div className="row" style={{ marginBottom: 22 }}>
          <button type="button" className={mode === "login" ? "btn-primary" : ""} onClick={() => { setMode("login"); setError(null); }}>
            Sign in
          </button>
          <button type="button" className={mode === "register" ? "btn-primary" : ""} onClick={() => { setMode("register"); setError(null); }}>
            Create account
          </button>
        </div>
        <form onSubmit={submit}>
          {mode === "register" && (
            <div className="field">
              <label htmlFor="displayName">Display name (optional)</label>
              <input id="displayName" autoComplete="name" maxLength={120} value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
            </div>
          )}
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" type="email" autoComplete="email" required maxLength={254} value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="password">Password {mode === "register" ? "(at least 12 characters)" : ""}</label>
            <input id="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} required minLength={mode === "register" ? 12 : 1} maxLength={256} value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {error && <div className="notice bad" role="alert" style={{ marginBottom: 14 }}>{error}</div>}
          <button className="btn-primary" type="submit" disabled={busy} style={{ width: "100%" }}>
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>
      </div>
      <p className="muted" style={{ marginTop: 14 }}>
        Account creation currently does not include email verification or password recovery. Use a unique password and do not reuse a password from another service.
      </p>
      <p className="muted"><Link href="/" style={{ textDecoration: "underline" }}>Back to characters</Link></p>
    </main>
  );
}
