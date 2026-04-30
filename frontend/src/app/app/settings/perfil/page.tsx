"use client";

import { useEffect, useState } from "react";
import { getWorkspaceProfile, updateWorkspaceProfile } from "@/lib/api-settings";
import type { WorkspaceProfile } from "@/lib/settings-types";

export default function PerfilPage() {
  const [data, setData] = useState<WorkspaceProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    getWorkspaceProfile().then(setData).finally(() => setLoading(false));
  }, []);

  if (loading || !data) return <div>Carregando…</div>;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!data) return;
    setSaving(true);
    try {
      const next = await updateWorkspaceProfile(data);
      setData(next);
      setToast("Perfil atualizado");
      setTimeout(() => setToast(null), 2000);
    } finally {
      setSaving(false);
    }
  }

  function field<K extends keyof WorkspaceProfile>(key: K, label: string, type: string = "text") {
    return (
      <div className="settings-field" key={key}>
        <label className="settings-field-label">{label}</label>
        <input
          className="settings-input"
          type={type}
          value={(data?.[key] as string) ?? ""}
          onChange={(e) => setData(d => d ? ({ ...d, [key]: e.target.value }) : d)}
        />
      </div>
    );
  }

  return (
    <form onSubmit={save}>
      <h2 style={{ fontSize: 22, fontWeight: 480, marginBottom: 8 }}>Perfil de remetente</h2>
      <p style={{ color: "var(--text-muted)", marginBottom: 24, fontSize: 14 }}>
        Esses dados aparecem na LP gerada, no email de outreach e nos templates de mensagem.
      </p>

      {field("business_name", "Nome do negócio")}
      {field("your_name", "Seu nome")}
      {field("your_email", "Seu email", "email")}
      {field("your_whatsapp", "Seu WhatsApp", "tel")}
      {field("your_website", "Seu site", "url")}

      <div className="settings-actions">
        <button type="submit" className="settings-btn settings-btn-primary" disabled={saving}>
          {saving ? "Salvando…" : "Salvar"}
        </button>
        {toast && <span style={{ fontSize: 14, color: "var(--ok)", alignSelf: "center" }}>{toast}</span>}
      </div>
    </form>
  );
}
