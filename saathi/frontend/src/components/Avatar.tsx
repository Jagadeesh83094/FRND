import type { CSSProperties } from "react";

const COLORS: Record<string, [string, string]> = {
  best_friend: ["#ffd166", "#ff8a5b"],
  mom: ["#ffb4c8", "#ff7ea8"],
  dad: ["#9fd6ff", "#5b8cff"],
  grandmother: ["#ffd9a0", "#e0a24d"],
  grandfather: ["#c8d3ff", "#7d8cff"],
  sibling: ["#b7f5d4", "#4fd39a"],
  mentor: ["#d5c2ff", "#9a7bff"],
  custom: ["#ffc9ec", "#c47bff"],
  default: ["#d9d4ff", "#8a7bff"],
};

const INITIALS: Record<string, string> = {
  best_friend: "BF",
  mom: "AM",
  dad: "NA",
  grandmother: "AM",
  grandfather: "TH",
  sibling: "SB",
  mentor: "ME",
  custom: "★",
};

export function Avatar({
  characterId,
  size = 64,
  avatarRef,
}: {
  characterId: string;
  size?: number;
  avatarRef?: string;
}) {
  const key = avatarRef && COLORS[avatarRef] ? avatarRef : characterId;
  const [a, b] = COLORS[key] || COLORS.default;
  const style: CSSProperties = {
    width: size,
    height: size,
    background: `linear-gradient(140deg, ${a}, ${b})`,
    fontSize: size * 0.32,
  };
  return (
    <div className="avatar" style={style} aria-hidden>
      {INITIALS[characterId] || INITIALS[key] || "AI"}
    </div>
  );
}
