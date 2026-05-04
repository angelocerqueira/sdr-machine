"use client";

const DIMS = [
  { label: "SSL", value: 0, hint: "ausente" },
  { label: "MOBILE", value: 15, hint: "quebrado" },
  { label: "STACK", value: 60, hint: "Wix '19" },
  { label: "REVIEWS", value: 88, hint: "4.6 ★" },
];

export function MockupEntende() {
  return (
    <div className="rounded-lg p-6" style={{ border: "1px solid var(--line-2)", background: "var(--paper-1)" }}>
      <div className="flex items-baseline justify-between mb-1">
        <div style={{ color: "var(--ink-0)", fontSize: "14px", fontWeight: 500 }}>Padaria do Zé</div>
        <div className="font-mono" style={{ color: "var(--ink-3)", fontSize: "11px" }}>PINHEIROS · SP</div>
      </div>
      <div className="font-mono mb-4" style={{ color: "var(--ink-3)", fontSize: "10px", letterSpacing: "0.18em", textTransform: "uppercase" }}>
        DIAGNÓSTICO DE PRESENÇA DIGITAL
      </div>
      <div className="flex items-center gap-6 mb-6">
        <div
          className="font-mono tabular-nums"
          style={{ color: "var(--danger)", fontSize: "64px", fontWeight: 600, lineHeight: 0.9, letterSpacing: "-0.03em" }}
        >
          87
        </div>
        <div>
          <div className="font-mono mb-1" style={{ color: "var(--ink-3)", fontSize: "11px", letterSpacing: "0.18em", textTransform: "uppercase" }}>
            SCORE
          </div>
          <div style={{ color: "var(--danger)", fontSize: "12px", fontWeight: 500 }}>Aja agora</div>
        </div>
      </div>
      <div className="space-y-3">
        {DIMS.map((d) => (
          <div key={d.label}>
            <div className="flex justify-between font-mono mb-1" style={{ fontSize: "11px" }}>
              <span style={{ color: "var(--ink-3)" }}>{d.label}</span>
              <span style={{ color: "var(--ink-2)" }}>{d.hint}</span>
            </div>
            <div className="rounded-full overflow-hidden" style={{ height: "4px", background: "var(--paper-2)" }}>
              <div
                className="h-full rounded-full"
                style={{
                  width: `${d.value}%`,
                  background: d.value < 30 ? "var(--danger)" : d.value < 70 ? "var(--warn)" : "var(--ok)",
                }}
              />
            </div>
          </div>
        ))}
      </div>
      <div className="mt-5 pt-4" style={{ borderTop: "1px solid var(--line-2)" }}>
        <div className="font-mono mb-2" style={{ color: "var(--ink-3)", fontSize: "10px", letterSpacing: "0.18em", textTransform: "uppercase" }}>
          RAZÕES
        </div>
        <ul className="space-y-1" style={{ color: "var(--ink-2)", fontSize: "12px" }}>
          <li>· Site sem HTTPS</li>
          <li>· Stack desatualizado (Wix 2019)</li>
          <li>· Sem breakpoint mobile</li>
        </ul>
      </div>
    </div>
  );
}
