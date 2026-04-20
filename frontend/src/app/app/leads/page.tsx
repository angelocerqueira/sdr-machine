"use client";

import { Icon } from "@/components/ui";
import { LaMaster } from "@/components/leads/la-master";
import { useLeadApp } from "@/components/leads/use-lead-app";
import { useRouter } from "next/navigation";

export default function LeadsEmptyPage() {
  const router = useRouter();
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
