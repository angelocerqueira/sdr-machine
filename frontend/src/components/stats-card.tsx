interface StatsCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  accent?: boolean;
}

export function StatsCard({ label, value, icon, accent }: StatsCardProps) {
  return (
    <div className={`rounded-xl border p-5 card-glow transition-default ${
      accent
        ? "border-accent/20 bg-accent-subtle"
        : "border-border bg-surface"
    }`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-text-secondary text-xs font-medium uppercase tracking-wider font-[family-name:var(--font-mono)]">
          {label}
        </span>
        <span className={`${accent ? "text-accent" : "text-text-muted"}`}>
          {icon}
        </span>
      </div>
      <p className={`stat-number text-3xl font-bold ${accent ? "text-accent" : "text-text"}`}>
        {value}
      </p>
    </div>
  );
}
