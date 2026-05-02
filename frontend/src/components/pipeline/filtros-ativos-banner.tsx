"use client";

import { useRouter, useSearchParams } from "next/navigation";

const FILTER_KEYS = [
  "search", "status", "nicho", "cidade",
  "score_min", "score_max", "has_telefone", "has_email",
  "perfil_lead", "nicho_canonico",
];

const LABELS: Record<string, string> = {
  search: "busca",
  status: "status",
  nicho: "nicho",
  cidade: "cidade",
  score_min: "score mín",
  score_max: "score máx",
  has_telefone: "telefone",
  has_email: "email",
  perfil_lead: "perfil",
  nicho_canonico: "nicho canônico",
};

export function FiltrosAtivosBanner() {
  const router = useRouter();
  const sp = useSearchParams();

  const active = FILTER_KEYS
    .map((k) => ({ key: k, value: sp.get(k) }))
    .filter((f): f is { key: string; value: string } => f.value !== null && f.value !== "");

  if (active.length === 0) return null;

  const clearAll = () => {
    const next = new URLSearchParams(sp.toString());
    for (const k of FILTER_KEYS) next.delete(k);
    router.replace(`?${next.toString()}`, { scroll: false });
  };

  const removeOne = (key: string) => {
    const next = new URLSearchParams(sp.toString());
    next.delete(key);
    router.replace(`?${next.toString()}`, { scroll: false });
  };

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border-subtle bg-surface-raised px-3 py-2 text-[13px]">
      <span className="t-eyebrow">Filtros ativos:</span>
      {active.map(({ key, value }) => (
        <button
          key={key}
          type="button"
          onClick={() => removeOne(key)}
          className="inline-flex items-center gap-1 rounded-md border border-border bg-surface px-2 py-0.5 text-text-secondary hover:text-text hover:border-border-strong transition-default cursor-pointer"
          title={`Remover ${LABELS[key] ?? key}`}
        >
          <span className="font-mono">{LABELS[key] ?? key}={value}</span>
          <span className="text-text-muted">⨯</span>
        </button>
      ))}
      <button
        type="button"
        onClick={clearAll}
        className="t-eyebrow text-accent hover:underline transition-default cursor-pointer"
      >
        Limpar tudo
      </button>
    </div>
  );
}
