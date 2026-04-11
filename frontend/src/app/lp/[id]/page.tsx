"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getLeadByPublicId } from "@/lib/api";
import { LpPreview } from "@/components/lp-preview";
import { ChatWidget } from "@/components/shared/chat-widget";
import { DigitalBlueprint } from "@/components/shared/digital-blueprint";
import { MissionControl } from "@/components/shared/mission-control";
import { buildChatDataForLead } from "@/lib/chat-templates";
import { leadToBlueprintData, leadToMissionControlData } from "@/lib/lead-to-practice";
import type { Lead } from "@/lib/types";

export default function LpPreviewPage() {
  const { id: publicId } = useParams<{ id: string }>();
  const [lead, setLead] = useState<Lead | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getLeadByPublicId(publicId)
      .then(setLead)
      .catch(() => setError(true));
  }, [publicId]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg">
        <p className="text-text-muted text-sm">LP nao encontrada</p>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg">
        <span className="w-5 h-5 border-2 border-text-muted border-t-accent rounded-full animate-spin" />
      </div>
    );
  }

  const chatData = buildChatDataForLead(lead);
  const blueprintData = leadToBlueprintData(lead);
  const missionData = leadToMissionControlData(lead);

  return (
    <div className="bg-bg min-h-screen">
      <LpPreview publicId={publicId} leadName={lead.nome} />

      <div className="max-w-5xl mx-auto px-6 py-16 space-y-20">
        <section>
          <div className="text-center mb-10">
            <p className="text-[11px] uppercase tracking-[4px] text-accent font-medium mb-3">Diagnostico Digital</p>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Analise completa: {lead.nome}
            </h2>
          </div>
          <DigitalBlueprint data={blueprintData} />
        </section>

        <section>
          <div className="text-center mb-10">
            <p className="text-[11px] uppercase tracking-[4px] text-accent font-medium mb-3">Mission Control</p>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Como voce vai acompanhar tudo
            </h2>
          </div>
          <MissionControl data={missionData} />
        </section>
      </div>

      <ChatWidget data={chatData} />
    </div>
  );
}
