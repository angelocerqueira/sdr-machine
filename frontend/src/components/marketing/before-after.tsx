"use client";

import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";

interface TransformPair {
  before: { label: string; detail: string };
  after: { label: string; detail: string };
}

const TRANSFORMS: TransformPair[] = [
  {
    before: { label: "Planilha bagunçada", detail: "Duplicatas, dados incompletos, versões perdidas" },
    after: { label: "Pipeline automático", detail: "Leads deduplicados, dados completos, tudo organizado" },
  },
  {
    before: { label: "47 abas abertas", detail: "Buscando negócios um por um, copiando e colando" },
    after: { label: "Uma interface", detail: "Scraping automático, resultados centralizados" },
  },
  {
    before: { label: "4-6h por dia", detail: "Prospectando manualmente, repetindo o mesmo processo" },
    after: { label: "15 minutos", detail: "Pra configurar — o resto roda sozinho" },
  },
  {
    before: { label: "Copy-paste de mensagens", detail: "Mensagens genéricas enviadas uma a uma" },
    after: { label: "3 mensagens personalizadas", detail: "Geradas por IA com dados reais de cada lead" },
  },
];

function TransformItem({ pair }: { pair: TransformPair }) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start 0.8", "start 0.3"],
  });

  const beforeOpacity = useTransform(scrollYProgress, [0, 0.4, 0.6, 1], [0, 1, 1, 0]);
  const afterOpacity = useTransform(scrollYProgress, [0.5, 0.8, 1], [0, 0.5, 1]);
  const beforeX = useTransform(scrollYProgress, [0.6, 1], [0, -30]);
  const afterX = useTransform(scrollYProgress, [0.5, 1], [30, 0]);

  return (
    <div ref={ref} className="min-h-[50vh] flex items-center justify-center px-6 py-12">
      <div className="max-w-4xl w-full grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
        {/* Before */}
        <motion.div
          style={{ opacity: beforeOpacity, x: beforeX }}
          className="rounded-xl border border-danger/20 bg-danger/[0.03] p-6"
        >
          <div className="text-[10px] uppercase tracking-[3px] text-danger font-medium mb-3">Antes</div>
          <h3 className="text-xl font-bold text-text mb-2">{pair.before.label}</h3>
          <p className="text-sm text-text-muted">{pair.before.detail}</p>
        </motion.div>

        {/* After */}
        <motion.div
          style={{ opacity: afterOpacity, x: afterX }}
          className="rounded-xl border border-accent/20 bg-accent-subtle p-6"
        >
          <div className="text-[10px] uppercase tracking-[3px] text-accent font-medium mb-3">Depois</div>
          <h3 className="text-xl font-bold text-text mb-2">{pair.after.label}</h3>
          <p className="text-sm text-text-muted">{pair.after.detail}</p>
        </motion.div>
      </div>
    </div>
  );
}

export function BeforeAfter() {
  return (
    <section className="py-20">
      <div className="text-center mb-16 px-6">
        <motion.p
          className="text-[11px] uppercase tracking-[4px] text-accent font-medium mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          O Contraste
        </motion.p>
        <motion.h2
          className="text-3xl sm:text-4xl font-extrabold tracking-tight"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          Prospecção manual vs automática
        </motion.h2>
      </div>

      {TRANSFORMS.map((pair, i) => (
        <TransformItem key={i} pair={pair} />
      ))}
    </section>
  );
}
