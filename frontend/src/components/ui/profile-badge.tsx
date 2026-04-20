import { LEAD_PROFILE_LABEL, type LeadProfile } from "@/lib/types";

const STYLES: Record<LeadProfile, { bg: string; text: string; emoji?: string }> = {
  hot_no_site:   { bg: "bg-[var(--score-hot)]/15",  text: "text-[var(--score-hot)]",  emoji: "🔥" },
  hot_bad_site:  { bg: "bg-[var(--score-hot)]/15",  text: "text-[var(--score-hot)]",  emoji: "🔥" },
  warm:          { bg: "bg-[var(--score-warm)]/15", text: "text-[var(--score-warm)]" },
  cold:          { bg: "bg-[var(--score-cool)]/15", text: "text-[var(--score-cool)]" },
  disqualified:  { bg: "bg-[var(--surface-2)]",     text: "text-[var(--text-muted)]" },
};

export function ProfileBadge({
  profile,
  showEmoji = true,
  size = "sm",
  className,
}: {
  profile: LeadProfile | null | undefined;
  showEmoji?: boolean;
  size?: "sm" | "md";
  className?: string;
}) {
  if (!profile) return null;
  const style = STYLES[profile];
  const label = LEAD_PROFILE_LABEL[profile];
  const sizeClass = size === "sm" ? "px-1.5 py-0.5 text-[11px]" : "px-2 py-1 text-xs";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md font-medium ${sizeClass} ${style.bg} ${style.text}${className ? ` ${className}` : ""}`}
      title={label}
    >
      {showEmoji && style.emoji && <span>{style.emoji}</span>}
      <span>{label}</span>
    </span>
  );
}
