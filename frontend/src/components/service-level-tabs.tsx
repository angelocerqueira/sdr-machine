"use client";

import { useState } from "react";
import type { ServiceLevels, NivelScore, NivelKey } from "@/lib/types";

const NIVEL_LABELS: Record<NivelKey, string> = {
  lp: "LP",
  automacao_basica: "Automação",
  mapa_automacoes: "Mapa+Auto",
  vertical_os: "OS",
};

const NIVEL_FULL_LABELS: Record<NivelKey, string> = {
  lp: "Landing Page",
  automacao_basica: "Automação Básica",
  mapa_automacoes: "Mapa + Automações",
  vertical_os: "Vertical OS",
};

const NIVEL_ORDER: NivelKey[] = ["lp", "automacao_basica", "mapa_automacoes", "vertical_os"];

function scoreColor(score: number): string {
  if (score >= 60) return "text-accent";
  if (score >= 40) return "text-warning";
  return "text-text-muted";
}

function scoreBgColor(score: number): string {
  if (score >= 60) return "bg-accent";
  if (score >= 40) return "bg-warning";
  return "bg-text-muted";
}

function ScoreBar({ score }: { score: number }) {
  return (
    <div className="w-full h-1.5 rounded-full bg-surface-overlay">
      <div
        className={`h-full rounded-full transition-all ${scoreBgColor(score)}`}
        style={{ width: `${score}%` }}
      />
    </div>
  );
}

function NivelDetail({ nivel, label }: { nivel: NivelScore; label: string }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-[11px] uppercase tracking-widest font-[family-name:var(--font-mono)] text-text-muted">
          {label}
        </h4>
        <span className={`text-[13px] font-bold font-[family-name:var(--font-mono)] ${scoreColor(nivel.score)}`}>
          {nivel.score}/100
        </span>
      </div>
      <ScoreBar score={nivel.score} />

      {nivel.sinais.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-widest font-[family-name:var(--font-mono)] text-text-muted mb-1.5">
            Sinais detectados
          </p>
          <div className="space-y-1">
            {nivel.sinais.map((sinal, i) => (
              <div key={i} className="flex items-start gap-2 text-[12px] text-text-secondary">
                <span className="w-1 h-1 rounded-full bg-text-muted shrink-0 mt-1.5" />
                {sinal}
              </div>
            ))}
          </div>
        </div>
      )}

      {nivel.oportunidades.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-widest font-[family-name:var(--font-mono)] text-text-muted mb-1.5">
            Oportunidades
          </p>
          <div className="flex flex-wrap gap-1.5">
            {nivel.oportunidades.map((opp, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-info/10 border border-info/20 text-[10px] text-info font-[family-name:var(--font-mono)]"
              >
                {opp}
              </span>
            ))}
          </div>
        </div>
      )}

      <p className="text-[12px] text-text-secondary leading-relaxed">
        {nivel.justificativa}
      </p>
    </div>
  );
}

interface ServiceLevelTabsProps {
  serviceLevels: ServiceLevels;
}

export function ServiceLevelTabs({ serviceLevels }: ServiceLevelTabsProps) {
  const [activeTab, setActiveTab] = useState<NivelKey>(serviceLevels.nivel_recomendado);

  const activeNivel = serviceLevels[activeTab] as NivelScore;

  return (
    <div className="space-y-4">
      {!serviceLevels.qualificado && serviceLevels.motivo_desqualificacao && (
        <div className="rounded-lg border border-danger/30 bg-danger/5 px-3 py-2">
          <p className="text-[11px] text-danger font-[family-name:var(--font-mono)]">
            Desqualificado: {serviceLevels.motivo_desqualificacao}
          </p>
        </div>
      )}

      <div className="rounded-xl border border-border bg-surface p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[10px] uppercase tracking-widest font-[family-name:var(--font-mono)] text-text-muted">
            Nível recomendado
          </span>
          <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-accent-subtle border border-accent/20 text-[11px] text-accent font-semibold font-[family-name:var(--font-mono)]">
            {NIVEL_FULL_LABELS[serviceLevels.nivel_recomendado]}
          </span>
        </div>
        <p className="text-[13px] text-text-secondary leading-relaxed">
          {serviceLevels.resumo_executivo}
        </p>
      </div>

      <div className="rounded-xl border border-border bg-surface overflow-hidden">
        <div className="flex border-b border-border">
          {NIVEL_ORDER.map((key) => {
            const nivel = serviceLevels[key] as NivelScore;
            const isActive = key === activeTab;
            const isRecommended = key === serviceLevels.nivel_recomendado;
            return (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`flex-1 flex flex-col items-center gap-0.5 px-2 py-2.5 transition-colors relative ${
                  isActive
                    ? "bg-surface-raised"
                    : "hover:bg-surface-raised/50"
                }`}
              >
                <span className={`text-[10px] font-[family-name:var(--font-mono)] uppercase tracking-wider ${
                  isActive ? "text-text" : "text-text-muted"
                }`}>
                  {NIVEL_LABELS[key]}
                </span>
                <span className={`text-[14px] font-bold font-[family-name:var(--font-mono)] ${scoreColor(nivel.score)}`}>
                  {nivel.score}
                </span>
                {isActive && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent" />
                )}
                {isRecommended && !isActive && (
                  <div className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-accent" />
                )}
              </button>
            );
          })}
        </div>

        <div className="p-4">
          <NivelDetail
            nivel={activeNivel}
            label={NIVEL_FULL_LABELS[activeTab]}
          />
        </div>
      </div>
    </div>
  );
}
