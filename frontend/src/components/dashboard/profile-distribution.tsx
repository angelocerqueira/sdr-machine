import Link from "next/link";
import { LEAD_PROFILE_LABEL, type LeadProfile } from "@/lib/types";

const ORDER: LeadProfile[] = [
  "hot_no_site", "hot_bad_site", "warm", "cold", "disqualified",
];

export function ProfileDistribution({
  data,
}: {
  data: Record<string, number>;
}) {
  const total = Object.values(data).reduce((a, b) => a + b, 0);

  return (
    <div className="rounded-xl border border-border bg-surface p-6">
      <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider font-[family-name:var(--font-mono)] mb-5">
        Distribuição por perfil
      </h3>
      {total > 0 ? (
        <ul className="distribution-list">
          {ORDER.map((p) => {
            const count = data[p] ?? 0;
            const pct = total > 0 ? Math.round((count / total) * 100) : 0;
            return (
              <li key={p}>
                <Link href={`/app/kanban?perfil_lead=${p}`} className="distribution-row">
                  <span className="label">{LEAD_PROFILE_LABEL[p]}</span>
                  <div className="bar">
                    <div className="fill" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="count">{count} ({pct}%)</span>
                </Link>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="text-text-muted text-xs">Nenhum lead classificado ainda</p>
      )}
    </div>
  );
}
