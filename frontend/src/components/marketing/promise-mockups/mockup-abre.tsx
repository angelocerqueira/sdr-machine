"use client";

const MSGS = [
  { when: "INICIAL · DIA 0", body: "Oi Zé, vi que o site da padaria não abre direito no celular. Tenho um esboço de como ficaria — quer dar uma olhada antes de a gente conversar?" },
  { when: "FOLLOW-UP · DIA 2", body: "E aí Zé, só dando ping. O esboço tá em padaria-do-ze.sdrmachine.com — 5 minutinhos de leitura." },
  { when: "FECHAMENTO · DIA 5", body: "Zé, última tentativa. Se fizer sentido, marcar 15 min essa semana. Senão, sumo daqui." },
];

export function MockupAbre() {
  return (
    <div className="space-y-3">
      {MSGS.map((m) => (
        <div key={m.when} className="rounded-md p-4" style={{ border: "1px solid var(--line-2)", background: "var(--paper-1)" }}>
          <div
            className="font-mono mb-2"
            style={{ color: "var(--ink-3)", fontSize: "10px", letterSpacing: "0.18em", textTransform: "uppercase" }}
          >
            {m.when}
          </div>
          <p style={{ color: "var(--ink-1)", fontSize: "13px", lineHeight: 1.6 }}>{m.body}</p>
        </div>
      ))}
      <a
        href="#"
        onClick={(e) => e.preventDefault()}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-md"
        style={{ background: "oklch(0.62 0.15 145)", color: "var(--paper-0)", fontSize: "12px", fontWeight: 500 }}
      >
        Abrir no WhatsApp →
      </a>
    </div>
  );
}
