"use client";

import { Icon } from "@/components/ui";
import { LaMaster } from "@/components/leads/la-master";
import { useRouter } from "next/navigation";

export default function LeadsEmptyPage() {
  const router = useRouter();

  return (
    <>
      <LaMaster
        activeId={-1}
        onSelect={(id) => router.push(`/app/leads/${id}`)}
      />
      <div className="la-work" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div className="state">
          <div className="state-icon">
            <Icon name="lead" size={20} />
          </div>
          <div className="state-title">Nenhum lead selecionado</div>
          <div className="state-msg">
            Selecione um lead na lista ao lado para ver o diagnóstico, landing page, mensagens e informações.
          </div>
        </div>
      </div>
    </>
  );
}
