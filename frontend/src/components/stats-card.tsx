interface StatsCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  accent?: boolean;
}

export function StatsCard({ label, value, icon, accent }: StatsCardProps) {
  return (
    <div className={`rounded-lg border p-4 card-glow transition-all duration-150 ${
      accent
        ? "border-accent/20 bg-accent-subtle"
        : "border-border-subtle bg-surface"
    }`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-text-muted text-[10px] font-medium uppercase tracking-[0.08em] font-[family-name:var(--font-mono)]">
          {label}
        </span>
        <span className={`${accent ? "text-accent" : "text-text-muted"}`}>
          {icon}
        </span>
      </div>
      <p className={`stat-number text-2xl font-bold ${accent ? "text-accent" : "text-text"}`}>
        {value}
      </p>
    </div>
  );
}
