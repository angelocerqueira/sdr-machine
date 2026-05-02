"use client";

import { useSearchParams } from "next/navigation";
import { KanbanBoard } from "@/components/kanban-board";
import type { LeadProfile, NichoCanonico } from "@/lib/types";

export function PipelineKanban() {
  const sp = useSearchParams();
  return (
    <KanbanBoard
      filterNicho={sp.get("nicho") ?? ""}
      filterCidade={sp.get("cidade") ?? ""}
      filterScoreMin={sp.get("score_min") ?? ""}
      filterPerfil={(sp.get("perfil_lead") ?? "") as LeadProfile | ""}
      filterNichoCanon={(sp.get("nicho_canonico") ?? "") as NichoCanonico | ""}
      search={sp.get("search") ?? ""}
      orderBy={sp.get("order_by") ?? "score_desc"}
      hideInlineFilters={true}
    />
  );
}
