"use client";

import { Icon } from "@/components/ui";
import { DiagnosticPanel } from "@/components/diagnostic-panel";
import type { LeadAppDetail } from "./lead-app-types";

export function LaTabStrategy({ lead }: { lead: LeadAppDetail }) {
  const diag = lead.diagnostico_marketing;

  if (!diag) {
    return (
      <div className="state" style={{ margin: "32px auto" }}>
        <div className="state-icon">
          <Icon name="search" size={20} />
        </div>
        <div className="state-title">Estratégia não gerada</div>
        <div className="state-msg">
          Este lead ainda não tem diagnóstico de marketing. Execute o enriquecimento pra gerar.
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: "4px 0" }}>
      <DiagnosticPanel
        siteAnalysis={{ diagnostico_marketing: diag }}
        compact={false}
      />
    </div>
  );
}
