"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AgentChat } from "@/components/shared/agent-chat";
import { DigitalBlueprint } from "@/components/shared/digital-blueprint";
import { MissionControl } from "@/components/shared/mission-control";
import { LP_CHAT_DATA, LP_BLUEPRINT_DATA, LP_MISSION_DATA } from "@/lib/practice-data";
import { lpDuration, lpEase } from "./lp-motion";

const TABS = [
  { key: "blueprint", label: "Diagnóstico" },
  { key: "chat", label: "Atendimento" },
  { key: "mission", label: "Mission Control" },
] as const;

type TabKey = typeof TABS[number]["key"];

export function PracticeBlock() {
  const [activeTab, setActiveTab] = useState<TabKey>("blueprint");

  return (
    <section id="pratica" className="relative py-24 px-6" style={{ background: "var(--paper-0)" }}>
      <div className="mx-auto max-w-5xl text-center mb-12">
        <div
          className="font-mono mb-4 inline-flex items-center gap-2"
          style={{ color: "var(--warn)", fontSize: "10px", letterSpacing: "0.18em", textTransform: "uppercase" }}
        >
          <span style={{ width: "16px", height: "1px", background: "var(--warn)" }} />
          DEMONSTRAÇÃO
        </div>
        <h2
          className="font-sans mb-3"
          style={{ color: "var(--ink-0)", fontSize: "clamp(28px, 4.5vw, 44px)", letterSpacing: "-0.025em", lineHeight: 1.1, fontWeight: 480 }}
        >
          Veja em prática. Sem rodar nada.
        </h2>
        <p style={{ color: "var(--ink-2)", fontSize: "15px", lineHeight: 1.55, maxWidth: "560px", margin: "0 auto" }}>
          Escolha um aspecto do produto e veja o que sairia da máquina pra um lead real.
        </p>
      </div>

      <div className="mx-auto max-w-5xl">
        <div
          className="flex justify-center gap-1 mb-8 rounded-md p-1 w-fit mx-auto"
          style={{ border: "1px solid var(--line-2)", background: "var(--paper-1)" }}
        >
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              className="px-4 py-2 rounded transition-colors"
              style={{
                fontSize: "13px",
                fontWeight: 500,
                background: activeTab === t.key ? "var(--paper-3)" : "transparent",
                color: activeTab === t.key ? "var(--ink-0)" : "var(--ink-3)",
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: lpDuration.fast, ease: lpEase }}
            className="rounded-lg p-6"
            style={{ border: "1px solid var(--line-2)", background: "var(--paper-1)" }}
          >
            {activeTab === "chat" && <AgentChat data={LP_CHAT_DATA} />}
            {activeTab === "blueprint" && <DigitalBlueprint data={LP_BLUEPRINT_DATA} />}
            {activeTab === "mission" && <MissionControl data={LP_MISSION_DATA} />}
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}
