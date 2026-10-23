import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Saathi — talk to someone",
  description:
    "A multi-character, voice-first AI companion. Every character is AI-generated.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <nav className="nav">
            <Link href="/" className="brand">
              <span className="dot" />
              Saathi
            </Link>
            <div className="nav-links">
              <Link href="/">Characters</Link>
              <Link href="/memories">Memories</Link>
              <Link href="/onboarding">About</Link>
              <Link href="/login">Sign in</Link>
            </div>
          </nav>
          {children}
        </div>
      </body>
    </html>
  );
}
