"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import type {
  MissionControlData,
  ActivityEvent,
  AgentPerformance,
  Integration,
} from "@/lib/practice-types";

// ─── Event type config ─────────────────────────────────────────────────────────

const EVENT_COLORS: Record<ActivityEvent["type"], string> = {
  lead: "#34d399",
  lp: "#60a5fa",
  resposta: "#fbbf24",
  outreach: "rgba(52,211,153,0.4)",
};

// ─── Status bar ────────────────────────────────────────────────────────────────

function StatusBar() {
  return (
    <div
      className="flex items-center justify-between px-4 py-2.5 rounded-xl border border-accent/10"
      style={{ background: "var(--color-accent-subtle)" }}
    >
      <div className="flex items-center gap-2.5">
        <span
          className="w-2 h-2 rounded-full bg-accent shrink-0"
          style={{
            boxShadow: "0 0 6px 2px rgba(52,211,153,0.5)",
          }}
        />
        <span className="text-[13px] font-semibold text-accent">
          Sistema Operando
        </span>
      </div>
      <div className="flex items-center gap-4">
        <span className="text-[11px] font-[family-name:var(--font-mono)] text-text-muted">
          Uptime: 99.8%
        </span>
        <span
          className="w-px h-3 shrink-0"
          style={{ background: "var(--color-border)" }}
        />
        <span className="text-[11px] font-[family-name:var(--font-mono)] text-text-muted">
          Ultima sync: 2min
        </span>
      </div>
    </div>
  );
}

// ─── KPI card ──────────────────────────────────────────────────────────────────

interface KpiCardProps {
  value: string;
  label: string;
  variation: string;
  highlight?: boolean;
  theme?: "green" | "blue";
}

function KpiCard({
  value,
  label,
  variation,
  highlight = false,
  theme = "green",
}: KpiCardProps) {
  const accentColor = theme === "blue" ? "#60a5fa" : "var(--color-accent)";
  const borderColor =
    theme === "blue"
      ? highlight
        ? "rgba(96,165,250,0.3)"
        : "rgba(96,165,250,0.15)"
      : highlight
        ? "rgba(52,211,153,0.3)"
        : "var(--color-border-subtle)";
  const bgColor =
    theme === "blue"
      ? "rgba(96,165,250,0.03)"
      : highlight
        ? "rgba(52,211,153,0.04)"
        : "rgba(255,255,255,0.02)";

  return (
    <div
      className="rounded-xl p-3.5 flex flex-col gap-1"
      style={{
        border: `1px solid ${borderColor}`,
        background: bgColor,
      }}
    >
      <p
        className="stat-number font-extrabold leading-none"
        style={{
          fontSize: "22px",
          color: highlight || theme === "blue" ? accentColor : "var(--color-text)",
        }}
      >
        {value}
      </p>
      <p
        className="font-[family-name:var(--font-mono)] uppercase tracking-widest"
        style={{ fontSize: "8px", color: "var(--color-text-muted)" }}
      >
        {label}
      </p>
      <p
        className="font-[family-name:var(--font-mono)]"
        style={{
          fontSize: "8px",
          color:
            theme === "blue"
              ? "rgba(96,165,250,0.7)"
              : "var(--color-accent-dim)",
        }}
      >
        {variation}
      </p>
    </div>
  );
}

// ─── KPI rows ─────────────────────────────────────────────────────────────────

interface KpiRowsProps {
  pipeline: MissionControlData["pipeline"];
  aiMetrics: MissionControlData["aiMetrics"];
}

function KpiRows({ pipeline, aiMetrics }: KpiRowsProps) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 16 }}
      animate={inView ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="flex flex-col gap-3"
    >
      {/* Row 1 — Pipeline */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
        <KpiCard
          value={pipeline.leadsCaptados.toLocaleString("pt-BR")}
          label="Leads captados"
          variation="+18% vs mes anterior"
        />
        <KpiCard
          value={pipeline.outreachEnviado.toLocaleString("pt-BR")}
          label="Outreach enviado"
          variation="89% entregues"
        />
        <KpiCard
          value={pipeline.respostas.toLocaleString("pt-BR")}
          label="Respostas"
          variation="19.6% taxa"
        />
        <KpiCard
          value={pipeline.reunioes.toLocaleString("pt-BR")}
          label="Reunioes"
          variation="6.7% conversao"
          highlight
        />
      </div>

      {/* Row 2 — AI Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
        <KpiCard
          value={aiMetrics.custoPorLead}
          label="Custo por lead"
          variation="tokens + API calls"
          theme="blue"
        />
        <KpiCard
          value={aiMetrics.roiIA}
          label="ROI da IA"
          variation="R$523 investido / R$24.7k gerado"
          theme="blue"
        />
        <KpiCard
          value={aiMetrics.leadTimeMedio}
          label="Lead time medio"
          variation="scrape ate outreach pronto"
          theme="blue"
        />
        <KpiCard
          value={aiMetrics.taxaSucessoAgentes}
          label="Taxa sucesso agentes"
          variation="interacoes sem erro"
          theme="blue"
        />
      </div>
    </motion.div>
  );
}

// ─── Activity feed ─────────────────────────────────────────────────────────────

function ActivityFeed({ events }: { events: ActivityEvent[] }) {
  return (
    <div className="flex flex-col gap-2">
      <p
        className="font-[family-name:var(--font-mono)] uppercase tracking-widest mb-1"
        style={{ fontSize: "9px", color: "var(--color-text-muted)" }}
      >
        Feed de Atividade
      </p>
      <div className="flex flex-col gap-2">
        {events.map((event, i) => {
          const color = EVENT_COLORS[event.type];
          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{
                duration: 0.35,
                ease: "easeOut",
                delay: 0.1 + i * 0.1,
              }}
              className="rounded-lg px-3 py-2.5 flex flex-col gap-0.5"
              style={{
                borderLeft: `2px solid ${color}`,
                background: "rgba(255,255,255,0.025)",
                border: `1px solid rgba(255,255,255,0.05)`,
                borderLeftColor: color,
                borderLeftWidth: "2px",
              }}
            >
              <p
                className="text-[11px] font-semibold leading-snug"
                style={{ color }}
              >
                {event.title}
              </p>
              <p
                className="text-[10px] leading-snug"
                style={{ color: "var(--color-text-secondary)" }}
              >
                {event.detail}
              </p>
              <p
                className="font-[family-name:var(--font-mono)] mt-0.5"
                style={{ fontSize: "9px", color: "var(--color-text-muted)" }}
              >
                {event.time}
              </p>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Pipeline funnel ───────────────────────────────────────────────────────────

interface FunnelRowProps {
  label: string;
  count: number;
  widthPercent: number;
  opacity: number;
  index: number;
}

function FunnelRow({ label, count, widthPercent, opacity, index }: FunnelRowProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.35, ease: "easeOut", delay: 0.15 + index * 0.08 }}
      className="flex flex-col gap-1"
    >
      <div className="flex items-center justify-between">
        <span
          className="text-[11px] font-medium"
          style={{ color: "var(--color-text-secondary)" }}
        >
          {label}
        </span>
        <span
          className="font-[family-name:var(--font-mono)] text-[11px] font-bold stat-number"
          style={{ color: "var(--color-text)" }}
        >
          {count.toLocaleString("pt-BR")}
        </span>
      </div>
      <div
        className="h-1.5 rounded-full overflow-hidden"
        style={{ background: "rgba(255,255,255,0.05)" }}
      >
        <div
          className="h-full rounded-full"
          style={{
            width: `${widthPercent}%`,
            background: `linear-gradient(90deg, rgba(52,211,153,${opacity}) 0%, rgba(52,211,153,${opacity * 0.6}) 100%)`,
          }}
        />
      </div>
    </motion.div>
  );
}

function PipelineFunnel({
  pipeline,
  integrations,
}: {
  pipeline: MissionControlData["pipeline"];
  integrations: Integration[];
}) {
  const funnelRows = [
    { label: "Captados", count: pipeline.leadsCaptados, widthPercent: 100, opacity: 0.8 },
    { label: "Analisados", count: Math.round(pipeline.leadsCaptados * 0.71), widthPercent: 71, opacity: 0.65 },
    { label: "Outreach", count: pipeline.outreachEnviado, widthPercent: 27, opacity: 0.5 },
    { label: "Fechados", count: pipeline.reunioes, widthPercent: 8, opacity: 0.35 },
  ];

  return (
    <div className="flex flex-col gap-4">
      <p
        className="font-[family-name:var(--font-mono)] uppercase tracking-widest"
        style={{ fontSize: "9px", color: "var(--color-text-muted)" }}
      >
        Funil do Pipeline
      </p>

      <div className="flex flex-col gap-3">
        {funnelRows.map((row, i) => (
          <FunnelRow key={row.label} {...row} index={i} />
        ))}
      </div>

      {/* Integrations */}
      <div className="flex flex-col gap-2 pt-2 border-t" style={{ borderColor: "var(--color-border-subtle)" }}>
        <p
          className="font-[family-name:var(--font-mono)] uppercase tracking-widest"
          style={{ fontSize: "9px", color: "var(--color-text-muted)" }}
        >
          Integracoes
        </p>
        <div className="flex flex-wrap gap-2">
          {integrations.map((integration) => {
            const dotColor = integration.status === "connected" ? "#34d399" : "#fbbf24";
            return (
              <div
                key={integration.name}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-full"
                style={{
                  background: "rgba(255,255,255,0.03)",
                  border: "1px solid rgba(255,255,255,0.07)",
                }}
              >
                <span
                  className="w-1 h-1 rounded-full shrink-0"
                  style={{ background: dotColor }}
                />
                <span
                  className="font-[family-name:var(--font-mono)] text-[10px]"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  {integration.name}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ─── Agent performance ─────────────────────────────────────────────────────────

function AgentCard({ agent, index }: { agent: AgentPerformance; index: number }) {
  const isGood = agent.successRate >= 90;
  const barColor = isGood ? "#34d399" : "#fbbf24";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut", delay: 0.1 + index * 0.08 }}
      className="flex flex-col gap-1.5 py-2.5 border-b last:border-b-0"
      style={{ borderColor: "rgba(255,255,255,0.04)" }}
    >
      <div className="flex items-center justify-between">
        <span
          className="text-[11px] font-medium"
          style={{ color: "var(--color-text)" }}
        >
          {agent.name}
        </span>
        <span
          className="font-[family-name:var(--font-mono)] text-[11px] font-bold stat-number"
          style={{ color: barColor }}
        >
          {agent.successRate}%
        </span>
      </div>
      <div
        className="h-1 rounded-full overflow-hidden"
        style={{ background: "rgba(255,255,255,0.05)" }}
      >
        <div
          className="h-full rounded-full"
          style={{
            width: `${agent.successRate}%`,
            background: barColor,
            opacity: 0.7,
          }}
        />
      </div>
      <div className="flex items-center gap-3">
        <span
          className="font-[family-name:var(--font-mono)]"
          style={{ fontSize: "9px", color: "var(--color-text-muted)" }}
        >
          {agent.calls.toLocaleString("pt-BR")} calls
        </span>
        <span
          className="w-px h-2.5 shrink-0"
          style={{ background: "var(--color-border-subtle)" }}
        />
        <span
          className="font-[family-name:var(--font-mono)]"
          style={{ fontSize: "9px", color: "var(--color-text-muted)" }}
        >
          {agent.cost}
        </span>
      </div>
    </motion.div>
  );
}

function AgentPerformancePanel({
  agents,
  tokensSummary,
}: {
  agents: AgentPerformance[];
  tokensSummary: MissionControlData["tokensSummary"];
}) {
  return (
    <div className="flex flex-col gap-4">
      <p
        className="font-[family-name:var(--font-mono)] uppercase tracking-widest"
        style={{ fontSize: "9px", color: "rgba(96,165,250,0.7)" }}
      >
        Performance dos Agentes
      </p>

      <div className="flex flex-col">
        {agents.map((agent, i) => (
          <AgentCard key={agent.name} agent={agent} index={i} />
        ))}
      </div>

      {/* Token summary */}
      <div
        className="rounded-xl p-3 flex flex-col gap-1.5"
        style={{
          border: "1px solid rgba(96,165,250,0.1)",
          background: "rgba(96,165,250,0.04)",
        }}
      >
        <div className="flex items-center justify-between">
          <span
            className="font-[family-name:var(--font-mono)] text-[10px]"
            style={{ color: "rgba(96,165,250,0.6)" }}
          >
            Tokens consumidos
          </span>
          <span
            className="font-[family-name:var(--font-mono)] text-[11px] font-bold stat-number"
            style={{ color: "rgba(96,165,250,0.9)" }}
          >
            {tokensSummary.tokensConsumed}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span
            className="font-[family-name:var(--font-mono)] text-[10px]"
            style={{ color: "rgba(96,165,250,0.6)" }}
          >
            Custo total IA
          </span>
          <span
            className="font-[family-name:var(--font-mono)] text-[11px] font-bold stat-number"
            style={{ color: "rgba(96,165,250,0.9)" }}
          >
            {tokensSummary.totalCost}
          </span>
        </div>
        <div className="flex items-center justify-between pt-1 border-t" style={{ borderColor: "rgba(96,165,250,0.08)" }}>
          <span
            className="font-[family-name:var(--font-mono)] text-[10px]"
            style={{ color: "rgba(96,165,250,0.6)" }}
          >
            Receita atribuida
          </span>
          <span
            className="font-[family-name:var(--font-mono)] text-[11px] font-bold stat-number"
            style={{ color: "var(--color-accent)" }}
          >
            {tokensSummary.revenueAttributed}
          </span>
        </div>
      </div>
    </div>
  );
}

// ─── Three-column grid ─────────────────────────────────────────────────────────

function ThreeColumnGrid({ data }: { data: MissionControlData }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* Left — Activity Feed */}
      <div
        className="rounded-2xl p-4"
        style={{
          background: "rgba(255,255,255,0.025)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <ActivityFeed events={data.feed} />
      </div>

      {/* Center — Pipeline Funnel */}
      <div
        className="rounded-2xl p-4"
        style={{
          background: "rgba(255,255,255,0.025)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <PipelineFunnel
          pipeline={data.pipeline}
          integrations={data.integrations}
        />
      </div>

      {/* Right — Agent Performance */}
      <div
        className="rounded-2xl p-4"
        style={{
          background: "rgba(255,255,255,0.025)",
          border: "1px solid rgba(96,165,250,0.06)",
        }}
      >
        <AgentPerformancePanel
          agents={data.agents}
          tokensSummary={data.tokensSummary}
        />
      </div>
    </div>
  );
}

// ─── Main MissionControl component ────────────────────────────────────────────

export function MissionControl({ data }: { data: MissionControlData }) {
  return (
    <div className="w-full flex justify-center">
      <div className="w-full max-w-3xl lg:max-w-[60%] mx-auto flex flex-col gap-4">
        {/* Status bar */}
        <StatusBar />

        {/* KPI rows */}
        <KpiRows pipeline={data.pipeline} aiMetrics={data.aiMetrics} />

        {/* Three-column grid */}
        <ThreeColumnGrid data={data} />

        {/* Badge */}
        <div className="flex justify-center pt-1">
          <span
            className="inline-flex items-center px-3 py-1 rounded-full font-[family-name:var(--font-mono)] uppercase tracking-widest"
            style={{
              fontSize: "9px",
              color: "var(--color-text-muted)",
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            Dados ilustrativos — numeros reais variam por operacao
          </span>
        </div>
      </div>
    </div>
  );
}
