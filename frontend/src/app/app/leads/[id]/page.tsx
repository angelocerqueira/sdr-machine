"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useLeadApp } from "@/components/leads/use-lead-app";
import { useRailContext } from "../layout";
import { LaMaster } from "@/components/leads/la-master";
import { LaTopbar } from "@/components/leads/la-topbar";
import { LaHeader } from "@/components/leads/la-header";
import { LaTabStrip } from "@/components/leads/la-tab-strip";
import { LaRail } from "@/components/leads/la-rail";
import { LaTabDiag } from "@/components/leads/la-tab-diagnostico";
import { LaTabLp } from "@/components/leads/la-tab-landing-page";
import { LaTabMsgs } from "@/components/leads/la-tab-mensagens";
import { LaTabInfo } from "@/components/leads/la-tab-informacoes";
import { buildTabs, TAB_ACTIONS } from "@/components/leads/lead-app-mock";
import { getLeadLandingPages, runEnrich, runGenerate, runOutreach, streamJob } from "@/lib/api";
import { Icon } from "@/components/ui";
import type { LeadAppDetail } from "@/components/leads/lead-app-types";
import type { Lead, LandingPage, ServiceLevels } from "@/lib/types";

/** Map real API Lead to the LeadAppDetail shape expected by tab components */
function mapToDetail(lead: Lead, landingPages: LandingPage[]): LeadAppDetail {
  const sl = (lead.site_analysis as Record<string, unknown>)?.service_levels as ServiceLevels | undefined;

  return {
    id: lead.id,
    public_id: lead.public_id,
    nome: lead.nome,
    telefone: lead.telefone || "",
    website: lead.website || "",
    endereco: lead.endereco || "",
    cidade: lead.cidade || "",
    nicho: lead.nicho || "",
    categoria: lead.categoria || "",
    rating: lead.rating || 0,
    reviews_count: lead.reviews_count,
    top_reviews: lead.top_reviews || [],
    status: lead.status,
    opportunity_score: lead.opportunity_score ?? 0,
    scores: {
      acessibilidade: lead.score_acessibilidade ?? 0,
      lp: lead.score_lp ?? 0,
      automacao: lead.score_automacao ?? 0,
      mapa: lead.score_mapa ?? 0,
    },
    cnpj: lead.cnpj || "",
    razao_social: lead.razao_social || "",
    porte: lead.porte || "",
    cnae: lead.cnae || "",
    email: lead.email || "",
    socios: lead.socios || [],
    tech_stack: lead.tech_stack || [],
    opportunity_reasons: lead.opportunity_reasons || [],
    sources: (lead.enrichment_sources || []).map((s) => ({
      provider: s.provider,
      status: s.status === "success" ? "ok" : s.status === "skipped" ? "skip" : s.status,
      time: new Date(s.timestamp).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }),
      note: s.error || "",
    })),
    messages: [],
    recommendation: {
      level: lead.nivel_recomendado || "",
      label: lead.nivel_recomendado?.replace(/_/g, " ") || "Não definido",
    },
    service_levels: sl || null,
    lp_versions: landingPages.map((lp) => ({
      id: lp.id,
      v: lp.version,
      created: new Date(lp.created_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) +
        " \u00b7 " +
        new Date(lp.created_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }),
      active: lp.is_active,
    })),
    created_at: lead.created_at,
  };
}

export default function LeadPage() {
  const params = useParams();
  const router = useRouter();
  const activeId = Number(params.id);
  const { railOpen, setRailOpen } = useRailContext();

  const {
    activeTab,
    setActiveTab,
    leads,
    leadsLoading,
    loadingMore,
    lead: rawLead,
    leadLoading,
    leadError,
    messages,
    currentIndex,
    total,
    hasMore,
    search,
    handleSearch,
    statusFilter,
    handleFilter,
    loadMore,
    refreshLead,
    refreshLeads,
    refreshMessages,
  } = useLeadApp(activeId);

  // Fetch landing pages
  const [landingPages, setLandingPages] = useState<LandingPage[]>([]);

  const fetchLandingPages = useCallback(() => {
    if (!activeId || activeId <= 0) return;
    getLeadLandingPages(activeId).then(setLandingPages).catch(() => setLandingPages([]));
  }, [activeId]);

  useEffect(() => { fetchLandingPages(); }, [fetchLandingPages]);

  const lead = rawLead ? mapToDetail(rawLead, landingPages) : null;

  // Inject real messages
  if (lead && messages.length > 0) {
    lead.messages = messages.map((m) => ({
      id: m.id,
      type: m.type,
      sent_at: m.sent_at,
      text: m.message_text,
      created_at: m.created_at,
    }));
  }

  const tabs = lead
    ? buildTabs({
        reasons: lead.opportunity_reasons.length,
        lpVersions: lead.lp_versions.length,
        messages: lead.messages.length,
      })
    : buildTabs({ reasons: 0, lpVersions: 0, messages: 0 });

  // ---- Tab actions ----
  const [actionLoading, setActionLoading] = useState(false);

  const handlePrimaryAction = useCallback(async () => {
    if (!lead || actionLoading) return;
    setActionLoading(true);
    try {
      let job;
      let onDone: () => void;
      switch (activeTab) {
        case "diag":
          job = await runEnrich({ lead_ids: [lead.id] });
          onDone = () => { refreshLead(); refreshLeads(); };
          break;
        case "lp":
          job = await runGenerate({ lead_ids: [lead.id] });
          onDone = () => { refreshLead(); fetchLandingPages(); refreshLeads(); };
          break;
        case "msgs":
          job = await runOutreach({ lead_ids: [lead.id] });
          onDone = () => { refreshMessages(); refreshLead(); refreshLeads(); };
          break;
        default:
          return;
      }
      // Stream SSE until job finishes, then refresh
      streamJob(job.id, (event) => {
        if (event.type === "done" || event.type === "error") {
          onDone();
          setActionLoading(false);
        }
      });
      return; // loading clears when SSE fires done/error
    } catch (e) {
      console.error("Erro na ação:", e);
      setActionLoading(false);
    }
  }, [lead, activeTab, actionLoading, refreshLead, refreshLeads, refreshMessages, fetchLandingPages]);

  const tabContent = () => {
    if (!lead) return null;
    switch (activeTab) {
      case "diag": return <LaTabDiag lead={lead} />;
      case "lp": return <LaTabLp lead={lead} onVersionActivated={fetchLandingPages} />;
      case "msgs": return <LaTabMsgs lead={lead} />;
      case "info": return <LaTabInfo lead={lead} />;
      default: return <LaTabDiag lead={lead} />;
    }
  };

  return (
    <>
      <LaMaster
        activeId={activeId}
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

      <div className="la-work">
        {leadLoading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flex: 1, gap: 8, color: "var(--text-muted)", fontSize: 13 }}>
            <span className="spin" />
            Carregando lead...
          </div>
        ) : leadError ? (
          <div className="state" style={{ margin: "auto" }}>
            <div className="state-icon" style={{ color: "var(--danger)" }}>
              <Icon name="error" size={20} />
            </div>
            <div className="state-title">Erro ao carregar lead</div>
            <div className="state-msg">{leadError}</div>
            <button className="btn btn-secondary btn-sm" onClick={() => router.refresh()}>
              <Icon name="refresh" size={14} /> Tentar novamente
            </button>
          </div>
        ) : lead ? (
          <>
            <LaTopbar
              lead={lead}
              railOpen={railOpen}
              setRailOpen={setRailOpen}
              position={currentIndex + 1}
              total={leads.length}
            />
            <LaHeader lead={lead} />
            <LaTabStrip
              activeTab={activeTab}
              setActiveTab={setActiveTab}
              tabs={tabs}
              actions={TAB_ACTIONS}
              onPrimaryAction={handlePrimaryAction}
              actionLoading={actionLoading}
            />
            <div className="la-body">
              {tabContent()}
            </div>
          </>
        ) : null}
      </div>

      {lead && <LaRail lead={lead} onLeadUpdated={() => { refreshLead(); refreshLeads(); }} />}
    </>
  );
}
