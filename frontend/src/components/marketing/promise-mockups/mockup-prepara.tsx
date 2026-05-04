"use client";

import { useMockupLoop } from "../lp-motion";

const ASSETS = [
  { kind: "Landing page", desc: "Hero + CTA + dor inline", color: "var(--accent)" },
  { kind: "Infográfico", desc: "Diagnóstico em 1 página A4", color: "var(--warn)" },
  { kind: "Mockup do site", desc: "Antes / depois lado a lado", color: "var(--danger)" },
];

export function MockupPrepara() {
  const active = useMockupLoop(ASSETS.length, 3500);
  return (
    <div className="grid grid-cols-3 gap-3">
      {ASSETS.map((a, i) => (
        <div
          key={a.kind}
          className="rounded-md p-3 flex flex-col justify-end transition-all"
          style={{
            aspectRatio: "3/4",
            background: "var(--paper-1)",
            border: `1px solid ${i === active ? a.color : "var(--line-2)"}`,
            boxShadow: i === active ? `0 0 0 2px color-mix(in oklch, ${a.color} 25%, transparent)` : "none",
            transform: i === active ? "translateY(-4px)" : "none",
          }}
        >
          <div
            className="flex-1 rounded mb-2"
            style={{
              background: i === active
                ? `linear-gradient(180deg, color-mix(in oklch, ${a.color} 18%, transparent), color-mix(in oklch, ${a.color} 4%, transparent))`
                : "var(--paper-2)",
            }}
          />
          <div style={{ color: "var(--ink-0)", fontSize: "12px", fontWeight: 500 }}>{a.kind}</div>
          <div className="font-mono leading-tight mt-1" style={{ color: "var(--ink-3)", fontSize: "10px" }}>{a.desc}</div>
        </div>
      ))}
    </div>
  );
}
