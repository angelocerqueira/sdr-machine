"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import type { BlueprintData, GapBlock } from "@/lib/practice-types";

// ─── Radar chart constants ─────────────────────────────────────────────────────

const RADAR_AXES = [
  { key: "seo", label: "SEO" },
  { key: "performance", label: "Performance" },
  { key: "mobile", label: "Mobile" },
  { key: "conteudo", label: "Conteudo" },
  { key: "seguranca", label: "Seguranca" },
  { key: "presenca", label: "Presenca" },
] as const;

type RadarAxisKey = (typeof RADAR_AXES)[number]["key"];

const MAX_RADIUS = 80;
const CENTER = 100;
const GRID_RINGS = [0.33, 0.66, 1.0];

function scoreToPoint(
  score: number,
  axisIndex: number,
  maxRadius: number = MAX_RADIUS
): [number, number] {
  const angle = (Math.PI * 2 * axisIndex) / 6 - Math.PI / 2;
  const r = (score / 100) * maxRadius;
  return [CENTER + r * Math.cos(angle), CENTER + r * Math.sin(angle)];
}

function pointsToPolygon(points: [number, number][]): string {
  return points.map(([x, y]) => `${x},${y}`).join(" ");
}

/** Build hexagon vertex at the given fraction of max radius */
function hexVertex(axisIndex: number, fraction: number): [number, number] {
  const angle = (Math.PI * 2 * axisIndex) / 6 - Math.PI / 2;
  const r = fraction * MAX_RADIUS;
  return [CENTER + r * Math.cos(angle), CENTER + r * Math.sin(angle)];
}

function scoreColor(score: number): string {
  if (score >= 70) return "#34d399";
  if (score >= 40) return "#fbbf24";
  return "#f87171";
}

// ─── Radar chart ───────────────────────────────────────────────────────────────

interface RadarChartProps {
  scores: BlueprintData["radarScores"];
  maturityScore: number;
  animate: boolean;
}

function RadarChart({ scores, maturityScore, animate }: RadarChartProps) {
  const scoreValues = RADAR_AXES.map((a) => scores[a.key as RadarAxisKey]);
  const idealPoints: [number, number][] = RADAR_AXES.map((_, i) =>
    hexVertex(i, 1.0)
  );
  const currentPoints: [number, number][] = RADAR_AXES.map((a, i) =>
    scoreToPoint(scores[a.key as RadarAxisKey], i)
  );
  const zeroPoints: [number, number][] = RADAR_AXES.map(() => [
    CENTER,
    CENTER,
  ]);

  const idealPolygonStr = pointsToPolygon(idealPoints);
  const currentPolygonStr = pointsToPolygon(currentPoints);
  const zeroPolygonStr = pointsToPolygon(zeroPoints);

  // Label positions — slightly further than max radius
  const labelPoints = RADAR_AXES.map((a, i) => {
    const angle = (Math.PI * 2 * i) / 6 - Math.PI / 2;
    const r = MAX_RADIUS + 14;
    return {
      x: CENTER + r * Math.cos(angle),
      y: CENTER + r * Math.sin(angle),
      label: a.label,
    };
  });

  return (
    <div className="flex flex-col items-center gap-4">
      <svg
        viewBox="0 0 200 200"
        className="w-full max-w-[260px]"
        aria-label="Radar de maturidade digital"
      >
        {/* Grid rings */}
        {GRID_RINGS.map((fraction, ri) => {
          const ringPoints = RADAR_AXES.map((_, i) => hexVertex(i, fraction));
          return (
            <polygon
              key={ri}
              points={pointsToPolygon(ringPoints)}
              fill="none"
              stroke="rgba(255,255,255,0.04)"
              strokeWidth="1"
            />
          );
        })}

        {/* Axis lines */}
        {RADAR_AXES.map((_, i) => {
          const [x, y] = hexVertex(i, 1.0);
          return (
            <line
              key={i}
              x1={CENTER}
              y1={CENTER}
              x2={x}
              y2={y}
              stroke="rgba(255,255,255,0.06)"
              strokeWidth="1"
            />
          );
        })}

        {/* Ideal shape */}
        <polygon
          points={idealPolygonStr}
          fill="rgba(52,211,153,0.04)"
          stroke="rgba(52,211,153,0.15)"
          strokeWidth="1.5"
          strokeDasharray="4 3"
        />

        {/* Current shape — animated */}
        <motion.polygon
          points={animate ? currentPolygonStr : zeroPolygonStr}
          initial={{ points: zeroPolygonStr }}
          animate={{ points: animate ? currentPolygonStr : zeroPolygonStr }}
          transition={{ duration: 1.1, ease: "easeOut", delay: 0.2 }}
          fill="rgba(248,113,113,0.08)"
          stroke="rgba(248,113,113,0.4)"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />

        {/* Vertex dots */}
        {currentPoints.map(([x, y], i) => (
          <circle
            key={i}
            cx={x}
            cy={y}
            r="3"
            fill={scoreColor(scoreValues[i])}
          />
        ))}

        {/* Axis labels */}
        {labelPoints.map(({ x, y, label }, i) => {
          // Determine text anchor based on horizontal position
          const anchor =
            x < CENTER - 5 ? "end" : x > CENTER + 5 ? "start" : "middle";
          return (
            <text
              key={i}
              x={x}
              y={y}
              textAnchor={anchor}
              dominantBaseline="central"
              fontSize="7.5"
              fill="var(--color-text-secondary)"
              fontFamily="var(--font-mono), monospace"
              style={{ fontFamily: "var(--font-mono), monospace" }}
            >
              {label}
            </text>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-1.5">
          <svg width="20" height="8">
            <line
              x1="0"
              y1="4"
              x2="20"
              y2="4"
              stroke="rgba(52,211,153,0.6)"
              strokeWidth="1.5"
              strokeDasharray="4 3"
            />
          </svg>
          <span className="text-[10px] font-[family-name:var(--font-mono)] text-text-muted uppercase tracking-wide">
            Ideal
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <svg width="20" height="8">
            <line
              x1="0"
              y1="4"
              x2="20"
              y2="4"
              stroke="rgba(248,113,113,0.6)"
              strokeWidth="1.5"
            />
          </svg>
          <span className="text-[10px] font-[family-name:var(--font-mono)] text-text-muted uppercase tracking-wide">
            Atual
          </span>
        </div>
      </div>

      {/* Maturity score */}
      <div className="text-center">
        <p
          className="text-4xl font-bold leading-none"
          style={{
            fontFamily: "var(--font-heading), system-ui, sans-serif",
            letterSpacing: "-0.03em",
            color:
              maturityScore >= 70
                ? "#34d399"
                : maturityScore >= 40
                  ? "#fbbf24"
                  : "#f87171",
          }}
        >
          {maturityScore}
          <span className="text-xl text-text-muted">/100</span>
        </p>
        <p className="text-[10px] font-[family-name:var(--font-mono)] text-text-muted uppercase tracking-widest mt-1">
          Maturidade Digital
        </p>
      </div>
    </div>
  );
}

// ─── Severity badge ────────────────────────────────────────────────────────────

const SEVERITY_CONFIG = {
  critico: {
    label: "CRITICO",
    borderClass: "border-[rgba(248,113,113,0.25)]",
    bgClass: "bg-[rgba(248,113,113,0.04)]",
    textClass: "text-[#f87171]",
    badgeBg: "bg-[rgba(248,113,113,0.12)]",
  },
  gap: {
    label: "GAP",
    borderClass: "border-[rgba(248,113,113,0.15)]",
    bgClass: "bg-[rgba(248,113,113,0.02)]",
    textClass: "text-[rgba(248,113,113,0.7)]",
    badgeBg: "bg-[rgba(248,113,113,0.08)]",
  },
  fraco: {
    label: "FRACO",
    borderClass: "border-[rgba(251,191,36,0.25)]",
    bgClass: "bg-[rgba(251,191,36,0.04)]",
    textClass: "text-[#fbbf24]",
    badgeBg: "bg-[rgba(251,191,36,0.12)]",
  },
} as const;

// ─── Gap block row ─────────────────────────────────────────────────────────────

interface GapRowProps {
  gap: GapBlock;
  index: number;
  isLast: boolean;
}

function GapRow({ gap, index, isLast }: GapRowProps) {
  const sev = SEVERITY_CONFIG[gap.severity];

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut", delay: 0.1 + index * 0.1 }}
      className="relative"
    >
      <div className="flex items-stretch gap-3">
        {/* Problem card */}
        <div
          className={`flex-1 rounded-xl border p-3 ${sev.borderClass} ${sev.bgClass}`}
        >
          <div className="flex items-center gap-2 mb-1.5">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-md text-[9px] font-bold font-[family-name:var(--font-mono)] uppercase tracking-widest ${sev.badgeBg} ${sev.textClass}`}
            >
              {sev.label}
            </span>
          </div>
          <p className={`text-[12px] font-semibold leading-snug mb-1 ${sev.textClass}`}>
            {gap.problem}
          </p>
          <p className="text-[11px] text-text-muted leading-relaxed">
            {gap.detail}
          </p>
        </div>

        {/* Arrow */}
        <div className="flex items-center shrink-0">
          <span className="text-text-muted text-sm">→</span>
        </div>

        {/* Solution card */}
        <div className="flex-1 rounded-xl border border-accent/20 bg-accent-subtle p-3">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[9px] font-bold font-[family-name:var(--font-mono)] uppercase tracking-widest bg-accent/10 text-accent">
              Solucao IA
            </span>
          </div>
          <p className="text-[12px] font-semibold text-accent leading-snug mb-1">
            {gap.solution}
          </p>
          <p className="text-[11px] text-text-muted leading-relaxed">
            {gap.solutionDetail}
          </p>
        </div>
      </div>

      {/* Vertical connector */}
      {!isLast && (
        <div
          className="absolute left-1/2 -translate-x-1/2 w-px bg-border-subtle"
          style={{ top: "100%", height: "12px" }}
        />
      )}
    </motion.div>
  );
}

// ─── Gap map panel ─────────────────────────────────────────────────────────────

function GapMap({ gaps }: { gaps: GapBlock[] }) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-[10px] font-[family-name:var(--font-mono)] text-text-muted uppercase tracking-widest mb-1">
        Mapa de Automacao
      </p>
      {gaps.map((gap, i) => (
        <GapRow
          key={i}
          gap={gap}
          index={i}
          isLast={i === gaps.length - 1}
        />
      ))}
    </div>
  );
}

// ─── Main DigitalBlueprint component ──────────────────────────────────────────

export function DigitalBlueprint({ data }: { data: BlueprintData }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <div
      ref={ref}
      className="w-full flex justify-center"
    >
      <div className="w-full max-w-3xl lg:max-w-[60%] mx-auto flex flex-col md:flex-row gap-6 md:gap-8 items-start">
        {/* Left panel — Radar chart (40%) */}
        <div className="w-full md:w-[40%] shrink-0">
          <div
            className="rounded-2xl border border-[rgba(255,255,255,0.07)] p-5"
            style={{
              background: "rgba(255,255,255,0.03)",
              backdropFilter: "blur(20px)",
              WebkitBackdropFilter: "blur(20px)",
            }}
          >
            <RadarChart
              scores={data.radarScores}
              maturityScore={data.maturityScore}
              animate={inView}
            />
          </div>
        </div>

        {/* Right panel — Gap map (60%) */}
        <div className="w-full md:w-[60%] min-w-0">
          <div
            className="rounded-2xl border border-[rgba(255,255,255,0.07)] p-5"
            style={{
              background: "rgba(255,255,255,0.03)",
              backdropFilter: "blur(20px)",
              WebkitBackdropFilter: "blur(20px)",
            }}
          >
            <GapMap gaps={data.gaps} />
          </div>
        </div>
      </div>
    </div>
  );
}
