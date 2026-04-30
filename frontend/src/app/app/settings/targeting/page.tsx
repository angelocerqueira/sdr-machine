"use client";

import { useEffect, useState } from "react";
import { getWorkspaceTargeting, updateWorkspaceTargeting } from "@/lib/api-settings";
import { ChipsInput } from "@/components/settings/chips-input";
import type { WorkspaceTargeting } from "@/lib/settings-types";

export default function TargetingPage() {
  const [data, setData] = useState<WorkspaceTargeting | null>(null);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    getWorkspaceTargeting().then(setData);
  }, []);

  if (!data) return <div>Carregando…</div>;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!data) return;
    setSaving(true);
    try {
      const next = await updateWorkspaceTargeting(data);
      setData(next);
      setToast("Targeting atualizado");
      setTimeout(() => setToast(null), 2000);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={save}>
      <h2 style={{ fontSize: 22, fontWeight: 480, marginBottom: 8 }}>Targeting</h2>
      <p style={{ color: "var(--text-muted)", marginBottom: 24, fontSize: 14 }}>
        Defaults pra novos jobs de scraping. Pode ser sobrescrito por job individual.
      </p>

      <div className="settings-field">
        <label className="settings-field-label">Nichos-alvo</label>
        <ChipsInput
          values={data.target_niches || []}
          onChange={(v) => setData(d => d ? ({ ...d, target_niches: v }) : d)}
          placeholder="dentista, pet shop…"
        />
      </div>

      <div className="settings-field">
        <label className="settings-field-label">Cidades-alvo</label>
        <ChipsInput
          values={data.target_cities || []}
          onChange={(v) => setData(d => d ? ({ ...d, target_cities: v }) : d)}
          placeholder="Chapecó SC, Florianópolis SC…"
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
        <div className="settings-field">
          <label className="settings-field-label">Rating mínimo (Google)</label>
          <input className="settings-input" type="number" step="0.1" min="0" max="5"
            value={data.min_rating ?? ""}
            onChange={(e) => setData(d => d ? ({ ...d, min_rating: e.target.value ? Number(e.target.value) : null }) : d)} />
        </div>
        <div className="settings-field">
          <label className="settings-field-label">Resultados por busca</label>
          <input className="settings-input" type="number" min="1" max="500"
            value={data.max_results_per_search ?? ""}
            onChange={(e) => setData(d => d ? ({ ...d, max_results_per_search: e.target.value ? Number(e.target.value) : null }) : d)} />
        </div>
        <div className="settings-field">
          <label className="settings-field-label">Score mínimo qualificação</label>
          <input className="settings-input" type="number" min="0" max="100"
            value={data.opportunity_score_threshold ?? ""}
            onChange={(e) => setData(d => d ? ({ ...d, opportunity_score_threshold: e.target.value ? Number(e.target.value) : null }) : d)} />
        </div>
      </div>

      <div className="settings-actions">
        <button type="submit" className="settings-btn settings-btn-primary" disabled={saving}>
          {saving ? "Salvando…" : "Salvar"}
        </button>
        {toast && <span style={{ fontSize: 14, color: "var(--ok)", alignSelf: "center" }}>{toast}</span>}
      </div>
    </form>
  );
}
