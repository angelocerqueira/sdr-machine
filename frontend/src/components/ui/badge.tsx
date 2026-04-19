interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "ok" | "warn" | "danger" | "accent";
  dot?: boolean;
  className?: string;
}

const variantClasses: Record<string, string> = {
  default: "bg-surface-raised text-text-body border-border",
  ok: "bg-ok-soft text-ok border-transparent",
  warn: "bg-warn-soft text-warn border-transparent",
  danger: "bg-danger-soft text-danger border-transparent",
  accent: "bg-accent-soft text-accent-ink border-transparent",
};

export function Badge({ children, variant = "default", dot = false, className = "" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 h-5 px-2 text-[11px] font-medium tracking-[0.01em] rounded-xs border whitespace-nowrap ${variantClasses[variant]} ${className}`}
    >
      {dot && <span className="w-1.5 h-1.5 rounded-full bg-current shrink-0" />}
      {children}
    </span>
  );
}
