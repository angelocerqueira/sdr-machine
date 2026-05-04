"use client";

const LEADS = [
  { name: "Padaria do Zé", meta: "Pinheiros · Padaria", score: 87, tone: "var(--danger)" },
  { name: "Auto Mec. Silva", meta: "Lapa · Mecânica", score: 92, tone: "var(--danger)" },
  { name: "Café Aurora", meta: "Vila Madalena · Cafeteria", score: 71, tone: "var(--warn)" },
  { name: "Studio Pilates Rê", meta: "Itaim · Pilates", score: 64, tone: "var(--warn)" },
  { name: "Pet Shop Bicho", meta: "Moema · Pet", score: 89, tone: "var(--danger)" },
];

export function MockupAcha() {
  return (
    <div className="rounded-lg overflow-hidden" style={{ border: "1px solid var(--line-2)", background: "var(--paper-1)" }}>
      <div
        className="px-4 py-3 flex items-center justify-between font-mono"
        style={{ borderBottom: "1px solid var(--line-2)", color: "var(--ink-3)", fontSize: "11px" }}
      >
        <span>5 LEADS · PADARIA × PINHEIROS</span>
        <span style={{ color: "var(--warn)" }}>FILTRO ATIVO</span>
      </div>
      <ul>
        {LEADS.map((l, idx) => (
          <li
            key={l.name}
            className="flex items-center justify-between px-4 py-3"
            style={{ borderBottom: idx === LEADS.length - 1 ? "none" : "1px solid var(--line-2)" }}
          >
            <div>
              <div style={{ color: "var(--ink-0)", fontSize: "14px", fontWeight: 500 }}>{l.name}</div>
              <div className="font-mono" style={{ color: "var(--ink-3)", fontSize: "11px" }}>{l.meta}</div>
            </div>
            <div className="font-mono tabular-nums" style={{ color: l.tone, fontSize: "14px", fontWeight: 600 }}>{l.score}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
