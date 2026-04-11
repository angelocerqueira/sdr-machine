"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface Feature {
  title: string;
  description: string;
  icon: string;
}

const FEATURES: Feature[] = [
  { title: "Enrichment Inteligente", description: "6 providers plugáveis — CNPJ, website, tech stack, email, Apollo, Schema.org", icon: "🔍" },
  { title: "WhatsApp Outreach", description: "3 mensagens por lead — abertura, follow-up 48h, fechamento com links personalizados", icon: "💬" },
  { title: "LPs com IA", description: "Landing pages personalizadas geradas por Claude, uma pra cada lead", icon: "🎨" },
  { title: "Opportunity Score", description: "10+ sinais — SSL, responsividade, PageSpeed, tech stack, SEO", icon: "📊" },
  { title: "Pipeline Visual", description: "Kanban drag-and-drop — acompanhe do scrape ao fechamento", icon: "📋" },
];

function HeroSlideScore() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 p-6">
      <div className="text-[10px] uppercase tracking-[3px] text-accent/60">Opportunity Score</div>
      <div className="flex items-end gap-1.5">
        {[25, 40, 55, 70, 50].map((h, i) => (
          <motion.div
            key={i}
            className="w-5 rounded-sm bg-accent/30"
            initial={{ height: 0 }}
            animate={{ height: h }}
            transition={{ delay: i * 0.1, duration: 0.4 }}
          />
        ))}
        <span className="ml-3 text-3xl font-extrabold text-accent stat-number">87</span>
      </div>
    </div>
  );
}

function HeroSlideKanban() {
  const cols = [
    { label: "Scraped", items: 3 },
    { label: "Enriched", items: 2 },
    { label: "Outreach", items: 1 },
    { label: "Closed", items: 1 },
  ];
  return (
    <div className="p-6 h-full flex flex-col">
      <div className="text-[10px] uppercase tracking-[3px] text-text-muted/60 mb-3">Pipeline Kanban</div>
      <div className="flex gap-2 flex-1">
        {cols.map((col) => (
          <div key={col.label} className="flex-1 bg-surface rounded-md p-2">
            <div className="text-[9px] text-text-muted mb-2">{col.label}</div>
            {Array.from({ length: col.items }).map((_, i) => (
              <div key={i} className="h-4 bg-accent/10 rounded mb-1.5" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function HeroSlideLP() {
  return (
    <div className="p-6 h-full flex flex-col items-center justify-center gap-3">
      <div className="text-[10px] uppercase tracking-[3px] text-text-muted/60">LP Gerada</div>
      <div className="w-full max-w-[200px] bg-surface rounded-lg border border-border-subtle p-3">
        <div className="h-2 bg-accent/20 rounded w-2/3 mb-2" />
        <div className="h-1.5 bg-surface-overlay rounded w-full mb-1" />
        <div className="h-1.5 bg-surface-overlay rounded w-4/5 mb-3" />
        <div className="h-5 bg-accent/15 rounded w-1/2" />
      </div>
    </div>
  );
}

const HERO_SLIDES = [
  { key: "score", component: <HeroSlideScore /> },
  { key: "kanban", component: <HeroSlideKanban /> },
  { key: "lp", component: <HeroSlideLP /> },
];

export function FeaturesGrid() {
  const [activeSlide, setActiveSlide] = useState(0);
  const [paused, setPaused] = useState(false);

  const nextSlide = useCallback(() => {
    setActiveSlide((prev) => (prev + 1) % HERO_SLIDES.length);
  }, []);

  useEffect(() => {
    if (paused) return;
    const interval = setInterval(nextSlide, 5000);
    return () => clearInterval(interval);
  }, [paused, nextSlide]);

  return (
    <section id="features" className="py-24 px-6">
      <div className="text-center mb-16 max-w-2xl mx-auto">
        <motion.p
          className="text-[11px] uppercase tracking-[4px] text-accent font-medium mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          Features
        </motion.p>
        <motion.h2
          className="text-3xl sm:text-4xl font-extrabold tracking-tight"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          Tudo que você precisa pra prospectar.
        </motion.h2>
      </div>

      <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-3 auto-rows-[140px]">
        {/* Hero card — spans 2x2 */}
        <motion.div
          className="md:col-span-2 md:row-span-2 rounded-xl border border-accent/15 bg-accent-subtle overflow-hidden cursor-pointer"
          onMouseEnter={() => setPaused(true)}
          onMouseLeave={() => setPaused(false)}
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
        >
          <div className="relative h-full">
            <AnimatePresence mode="wait">
              <motion.div
                key={HERO_SLIDES[activeSlide].key}
                className="absolute inset-0"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.4 }}
              >
                {HERO_SLIDES[activeSlide].component}
              </motion.div>
            </AnimatePresence>

            {/* Dots */}
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-1.5">
              {HERO_SLIDES.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setActiveSlide(i)}
                  className={`w-1.5 h-1.5 rounded-full transition-colors ${
                    i === activeSlide ? "bg-accent" : "bg-text-muted/30"
                  }`}
                />
              ))}
            </div>
          </div>
        </motion.div>

        {/* Feature cards */}
        {FEATURES.map((feat, i) => (
          <motion.div
            key={feat.title}
            className="rounded-xl border border-border bg-surface p-5 card-glow flex flex-col justify-between"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.08, duration: 0.4 }}
          >
            <div>
              <span className="text-lg mb-2 block">{feat.icon}</span>
              <h3 className="text-sm font-bold mb-1">{feat.title}</h3>
            </div>
            <p className="text-[11px] text-text-muted leading-relaxed">{feat.description}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
