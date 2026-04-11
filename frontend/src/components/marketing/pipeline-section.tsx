"use client";

import { motion } from "framer-motion";

interface PipelineStep {
  number: string;
  title: string;
  description: string;
  detail: string;
}

const STEPS: PipelineStep[] = [
  {
    number: "01",
    title: "Scrape",
    description: "Busca automática no Google Maps",
    detail: "Encontra centenas de negócios por nicho e cidade via Apify. Deduplicação automática.",
  },
  {
    number: "02",
    title: "Enrich",
    description: "6 providers de dados em paralelo",
    detail: "CNPJ, website, tech stack, email, Apollo, Schema.org — tudo numa passagem.",
  },
  {
    number: "03",
    title: "Generate",
    description: "Landing pages com IA",
    detail: "Claude gera uma LP personalizada pra cada lead, com dados reais do negócio.",
  },
  {
    number: "04",
    title: "Outreach",
    description: "Mensagens WhatsApp prontas",
    detail: "3 mensagens por lead — abertura, follow-up 48h e fechamento. Links wa.me pré-preenchidos.",
  },
];

export function PipelineSection() {
  return (
    <section id="como-funciona" className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <motion.p
            className="text-[11px] uppercase tracking-[4px] text-accent font-medium mb-4"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
          >
            Como Funciona
          </motion.p>
          <motion.h2
            className="text-3xl sm:text-4xl font-extrabold tracking-tight"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            Pipeline de 4 etapas, 100% automático.
          </motion.h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {STEPS.map((step, i) => (
            <motion.div
              key={step.number}
              className="relative rounded-xl border border-border bg-surface p-6 card-glow"
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.4 }}
            >
              {/* Connector line (not on last) */}
              {i < STEPS.length - 1 && (
                <div className="hidden lg:block absolute top-8 right-0 translate-x-1/2 w-4 h-px bg-border z-10" />
              )}

              <div className="text-[10px] font-mono text-accent/50 mb-3">{step.number}</div>
              <h3 className="text-base font-bold mb-1">{step.title}</h3>
              <p className="text-xs text-accent mb-3">{step.description}</p>
              <p className="text-[11px] text-text-muted leading-relaxed">{step.detail}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
