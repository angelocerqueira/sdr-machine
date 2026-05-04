"use client";

import { useEffect } from "react";
import { Icon } from "@/components/ui";
import { LaMaster } from "@/components/leads/la-master";
import { useLeadApp } from "@/components/leads/use-lead-app";
import { useRouter } from "next/navigation";

export default function LeadsEmptyPage() {
  const router = useRouter();

  // Redirect to last viewed lead, if any
  useEffect(() => {
    try {
      const lastId = localStorage.getItem("sdr-leads-active-id");
      if (lastId && /^\d+$/.test(lastId)) router.replace(`/app/leads/${lastId}`);
    } catch {}
  }, [router]);
  const {
    leads,
    leadsLoading,
    loadingMore,
    total,
    hasMore,
    search,
    handleSearch,
    statusFilter,
    handleFilter,
    perfilFilter,
    handlePerfilFilter,
    nichoCanonFilter,
    handleNichoCanonFilter,
    loadMore,
  } = useLeadApp(null);

  return (
    <>
      <LaMaster
        activeId={-1}
        onSelect={(id) => router.push(`/app/leads/${id}`)}
        leads={leads}
        loading={leadsLoading}
        loadingMore={loadingMore}
        hasMore={hasMore}
        total={total}
        onLoadMore={loadMore}
        search={search}
        onSearch={handleSearch}
        statusFilter={statusFilter}
        onFilter={handleFilter}
        perfilFilter={perfilFilter}
        onPerfilFilter={handlePerfilFilter}
        nichoCanonFilter={nichoCanonFilter}
        onNichoCanonFilter={handleNichoCanonFilter}
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
