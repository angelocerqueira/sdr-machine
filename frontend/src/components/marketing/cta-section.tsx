"use client";

import { motion } from "framer-motion";

export function CTASection() {
  return (
    <section id="agendar" className="relative py-32 px-6 overflow-hidden">
      {/* Animated gradient blobs */}
      <motion.div
        className="absolute -top-1/4 -left-1/4 w-[500px] h-[500px] rounded-full opacity-[0.04]"
        style={{ background: "radial-gradient(circle, #34d399, transparent 70%)" }}
        animate={{ x: [0, 40, 0], y: [0, -20, 0] }}
        transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute -bottom-1/4 -right-1/4 w-[400px] h-[400px] rounded-full opacity-[0.03]"
        style={{ background: "radial-gradient(circle, #34d399, transparent 70%)" }}
        animate={{ x: [0, -30, 0], y: [0, 30, 0] }}
        transition={{ duration: 15, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute top-1/3 right-1/4 w-[250px] h-[250px] rounded-full opacity-[0.03]"
        style={{ background: "radial-gradient(circle, #34d399, transparent 70%)" }}
        animate={{ x: [0, 20, 0], y: [0, -40, 0] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
      />

      <motion.div
        className="relative z-10 max-w-2xl mx-auto text-center"
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
      >
        <p className="text-[11px] uppercase tracking-[4px] text-accent font-medium mb-5">
          Comece agora
        </p>

        <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight mb-8">
          Pare de perder horas prospectando.
        </h2>

        {/* Mini stats */}
        <div className="flex justify-center gap-8 sm:gap-12 mb-10">
          {[
            { value: "4x", label: "mais leads" },
            { value: "90%", label: "menos tempo" },
            { value: "0", label: "trabalho manual" },
          ].map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-2xl sm:text-3xl font-extrabold text-accent stat-number">
                {stat.value}
              </div>
              <div className="text-[10px] sm:text-xs text-text-muted mt-1">{stat.label}</div>
            </div>
          ))}
        </div>

        {/* CTA button */}
        <a
          href="#agendar"
          className="inline-block bg-accent text-bg font-bold text-base sm:text-lg rounded-xl px-10 py-4 hover:bg-accent-dim transition-colors pulse-glow"
        >
          Agendar Demo Gratuita →
        </a>

        <p className="text-xs text-text-muted mt-5">
          Sem compromisso · 30 min · Veja funcionando ao vivo
        </p>
      </motion.div>
    </section>
  );
}
