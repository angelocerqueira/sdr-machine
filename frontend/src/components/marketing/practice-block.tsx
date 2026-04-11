"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AgentChat } from "@/components/shared/agent-chat";
import { DigitalBlueprint } from "@/components/shared/digital-blueprint";
import { MissionControl } from "@/components/shared/mission-control";
import { LP_CHAT_DATA, LP_BLUEPRINT_DATA, LP_MISSION_DATA } from "@/lib/practice-data";

const TABS = [
  { key: "chat", label: "Atendimento IA" },
  { key: "blueprint", label: "Blueprint Digital" },
  { key: "mission", label: "Mission Control" },
] as const;

type TabKey = typeof TABS[number]["key"];

export function PracticeBlock() {
  const [activeTab, setActiveTab] = useState<TabKey>("chat");

  return (
    <section className="py-24 px-6 relative overflow-hidden">
      {/* Ambient glow */}
      <div
        className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[500px] h-[500px] rounded-full pointer-events-none"
        style={{ background: "radial-gradient(circle, rgba(52,211,153,0.03) 0%, transparent 70%)" }}
      />

      {/* Header */}
      <div className="text-center mb-8 relative">
        <motion.p
          className="text-[11px] uppercase tracking-[4px] text-accent font-medium mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          Veja na Pratica
        </motion.p>
        <motion.h2
          className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-3"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          Seus clientes atendidos por IA. 24/7.
        </motion.h2>
        <motion.p
          className="text-text-secondary text-sm max-w-md mx-auto"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.1 }}
        >
          Explore cada aspecto da inteligencia que vamos aplicar no seu negocio.
        </motion.p>
      </div>

      {/* Tabs */}
      <div role="tablist" className="flex justify-center gap-1 mb-8">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={activeTab === tab.key}
            id={`tab-${tab.key}`}
            aria-controls={`panel-${tab.key}`}
            onClick={() => setActiveTab(tab.key)}
            className={`px-5 py-2.5 rounded-lg text-[13px] font-medium transition-all duration-200 ${
              activeTab === tab.key
                ? "bg-accent/10 border border-accent/30 text-accent"
                : "bg-white/[0.03] border border-white/[0.08] text-text-muted hover:text-text-secondary"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div role="tabpanel" id={`panel-${activeTab}`} aria-labelledby={`tab-${activeTab}`}>
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
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
