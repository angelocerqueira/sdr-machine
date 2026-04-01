"use client";

const FUNNEL_LABELS: Record<string, string> = {
  descoberta: "Descoberta",
  atracao: "Atração",
  consideracao: "Consideração",
  acao: "Ação",
  apologia: "Apologia",
};
const FUNNEL_ORDER = ["descoberta", "atracao", "consideracao", "acao", "apologia"];

interface FunnelAction {
  acao: string;
  resultado_esperado: string;
  kpi: string;
}

interface FunnelStage {
  diagnostico: string;
  acoes_top2: FunnelAction[];
}

interface IAPotential {
  score: number;
  oportunidades: string[];
  justificativa: string;
}

interface DiagnosticData {
  resumo_executivo: string;
  momento_funil: string;
  potencial_ia_automacao?: IAPotential;
  prioridades_top3?: string[];
  funil?: Record<string, FunnelStage>;
  qualificado?: boolean;
  motivo_desqualificacao?: string | null;
}

interface DiagnosticPanelProps {
  siteAnalysis: Record<string, unknown>;
  /** Compact mode hides funnel details (used in lead-detail page) */
  compact?: boolean;
}

export function DiagnosticPanel({ siteAnalysis, compact = false }: DiagnosticPanelProps) {
  const diag = siteAnalysis?.diagnostico_marketing as DiagnosticData | undefined;
  if (!diag) return null;

  const momento = diag.momento_funil;
  const iaPot = diag.potencial_ia_automacao;
  const prioridades = diag.prioridades_top3;
  const funil = diag.funil;

  return (
    <div className={compact ? "rounded-xl border border-border bg-surface p-5 space-y-5" : "space-y-4"}>
      {/* Resumo + momento funil */}
      <div className={compact ? "" : "rounded-xl border border-border bg-surface p-4"}>
        <h3 className="text-[10px] uppercase tracking-widest font-[family-name:var(--font-mono)] text-text-muted mb-3">
          Diagnóstico de Marketing
        </h3>
        <p className="text-[13px] text-text-secondary leading-relaxed mb-4">
          {diag.resumo_executivo}
        </p>

        {/* Disqualification notice */}
        {diag.qualificado === false && diag.motivo_desqualificacao && (
          <div className="rounded-lg border border-danger/30 bg-danger/5 px-3 py-2 mb-4">
            <p className="text-[11px] text-danger font-[family-name:var(--font-mono)]">
              Desqualificado: {diag.motivo_desqualificacao}
            </p>
          </div>
        )}

        {/* Funnel stages visualization */}
        <div className="flex gap-1 mb-2">
          {FUNNEL_ORDER.map((stage) => (
            <div
              key={stage}
              className={`flex-1 h-1.5 rounded-full transition-colors ${
                stage === momento
                  ? "bg-accent"
                  : FUNNEL_ORDER.indexOf(stage) < FUNNEL_ORDER.indexOf(momento)
                  ? "bg-accent/30"
                  : "bg-surface-overlay"
              }`}
              title={FUNNEL_LABELS[stage]}
            />
          ))}
        </div>
        <p className="text-[11px] font-[family-name:var(--font-mono)]">
          <span className="text-text-muted">{compact ? "Momento: " : "Momento atual: "}</span>
          <span className="text-accent font-medium">{FUNNEL_LABELS[momento] ?? momento}</span>
        </p>
      </div>

      {/* Potencial IA + Prioridades */}
      {compact ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {iaPot && <IAPotentialCard iaPot={iaPot} raised />}
          {prioridades && prioridades.length > 0 && <PrioridadesCard prioridades={prioridades} raised />}
        </div>
      ) : (
        <>
          {iaPot && <IAPotentialCard iaPot={iaPot} />}
          {prioridades && prioridades.length > 0 && <PrioridadesCard prioridades={prioridades} />}
        </>
      )}

      {/* Funnel details (collapsible, only in full mode) */}
      {!compact && funil && (
        <details className="rounded-xl border border-border bg-surface">
          <summary className="px-4 py-3 cursor-pointer text-[10px] uppercase tracking-widest font-[family-name:var(--font-mono)] text-text-muted hover:text-text transition-colors select-none">
            Detalhes por Etapa do Funil
          </summary>
          <div className="px-4 pb-4 space-y-4">
            {FUNNEL_ORDER.map((stage) => {
              const data = funil[stage];
              if (!data) return null;
              const isActive = stage === momento;
              return (
                <div
                  key={stage}
                  className={`rounded-lg border p-3 ${
                    isActive
                      ? "border-accent/30 bg-accent-subtle/30"
                      : "border-border-subtle bg-surface-raised"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    {isActive && <span className="w-1.5 h-1.5 rounded-full bg-accent" />}
                    <h4 className={`text-[11px] font-semibold uppercase tracking-wider font-[family-name:var(--font-mono)] ${
                      isActive ? "text-accent" : "text-text-muted"
                    }`}>
                      {FUNNEL_LABELS[stage]}
                    </h4>
                  </div>
                  <p className="text-[12px] text-text-secondary leading-relaxed mb-2">
                    {data.diagnostico}
                  </p>
                  {data.acoes_top2 && (
                    <div className="space-y-1.5">
                      {data.acoes_top2.map((acao, ai) => (
                        <div key={ai} className="flex items-start gap-2 text-[11px]">
                          <span className="text-accent mt-0.5">→</span>
                          <div>
                            <span className="text-text">{acao.acao}</span>
                            <span className="text-text-muted"> · {acao.resultado_esperado}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </details>
      )}
    </div>
  );
}

function IAPotentialCard({ iaPot, raised }: { iaPot: IAPotential; raised?: boolean }) {
  const base = raised
    ? "rounded-lg border border-border-subtle bg-surface-raised p-4"
    : "rounded-xl border border-border bg-surface p-4";

  return (
    <div className={base}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[10px] uppercase tracking-widest font-[family-name:var(--font-mono)] text-text-muted">
          Potencial IA & Automação
        </h3>
        <span className={`text-[13px] font-bold font-[family-name:var(--font-mono)] ${
          iaPot.score >= 60 ? "text-accent" : iaPot.score >= 40 ? "text-warning" : "text-text-muted"
        }`}>
          {iaPot.score}/100
        </span>
      </div>
      <div className="w-full h-1.5 rounded-full bg-surface-overlay mb-3">
        <div
          className={`h-full rounded-full transition-all ${
            iaPot.score >= 60 ? "bg-accent" : iaPot.score >= 40 ? "bg-warning" : "bg-text-muted"
          }`}
          style={{ width: `${iaPot.score}%` }}
        />
      </div>
      {!raised && iaPot.justificativa && (
        <p className="text-[12px] text-text-secondary leading-relaxed mb-3">
          {iaPot.justificativa}
        </p>
      )}
      <div className="flex flex-wrap gap-1.5">
        {iaPot.oportunidades.map((opp, i) => (
          <span
            key={i}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-info/10 border border-info/20 text-[10px] text-info font-[family-name:var(--font-mono)]"
          >
            {opp}
          </span>
        ))}
      </div>
    </div>
  );
}

function PrioridadesCard({ prioridades, raised }: { prioridades: string[]; raised?: boolean }) {
  const base = raised
    ? "rounded-lg border border-border-subtle bg-surface-raised p-4"
    : "rounded-xl border border-border bg-surface p-4";

  return (
    <div className={base}>
      <h3 className="text-[10px] uppercase tracking-widest font-[family-name:var(--font-mono)] text-text-muted mb-3">
        Top 3 Prioridades
      </h3>
      <div className="space-y-2">
        {prioridades.map((p, i) => (
          <div key={i} className="flex items-start gap-2.5">
            <span className="flex items-center justify-center w-5 h-5 rounded-md bg-accent-subtle text-[10px] font-bold text-accent font-[family-name:var(--font-mono)] shrink-0 mt-0.5">
              {i + 1}
            </span>
            <span className="text-[12px] text-text-secondary">{p}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
