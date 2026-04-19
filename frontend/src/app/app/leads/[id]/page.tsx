"use client";

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
import { LEAD_DETAIL, TABS, TAB_ACTIONS } from "@/components/leads/lead-app-mock";
import { Icon } from "@/components/ui";

export default function LeadPage() {
  const params = useParams();
  const router = useRouter();
  const activeId = Number(params.id);
  const { railOpen, setRailOpen } = useRailContext();

  const {
    activeTab,
    setActiveTab,
    theme,
    setTheme,
    currentIndex,
    total,
  } = useLeadApp(activeId);

  // TODO: fetch real lead data — for now use mock
  const lead = LEAD_DETAIL;

  const tabContent = () => {
    switch (activeTab) {
      case "diag": return <LaTabDiag lead={lead} />;
      case "lp": return <LaTabLp lead={lead} />;
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
      />

      <div className="la-work">
        <LaTopbar
          lead={lead}
          theme={theme}
          setTheme={setTheme}
          railOpen={railOpen}
          setRailOpen={setRailOpen}
          position={currentIndex + 1}
          total={total}
        />
        <LaHeader lead={lead} />
        <LaTabStrip
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          tabs={TABS}
          actions={TAB_ACTIONS}
        />
        <div className="la-body">
          {tabContent()}
        </div>
      </div>

      <LaRail lead={lead} />
    </>
  );
}
