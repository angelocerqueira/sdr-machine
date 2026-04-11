"use client";

import dynamic from "next/dynamic";
import { motion } from "framer-motion";

const Player = dynamic(
  () => import("@remotion/player").then((mod) => mod.Player),
  { ssr: false }
);

const HeroComposition = dynamic(
  () =>
    import("@/components/remotion/hero-composition").then(
      (mod) => mod.HeroComposition
    ),
  { ssr: false }
);

export function HeroSection() {
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden">
      {/* Remotion background */}
      <div className="absolute inset-0 z-0">
        <div className="w-full h-full" suppressHydrationWarning>
          {typeof window !== "undefined" && (
            <Player
              component={HeroComposition}
              compositionWidth={1920}
              compositionHeight={1080}
              durationInFrames={360}
              fps={30}
              style={{ width: "100%", height: "100%" }}
              autoPlay
              loop
              controls={false}
              showVolumeControls={false}
            />
          )}
        </div>
        {/* Gradient overlay for text readability */}
        <div className="absolute inset-0 bg-gradient-to-b from-bg/40 via-bg/60 to-bg" />
      </div>

      {/* Content */}
      <div className="relative z-10 text-center px-6 max-w-3xl mx-auto">
        <motion.p
          className="text-[11px] sm:text-xs uppercase tracking-[4px] text-accent font-medium mb-5"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          Prospecção Automatizada com IA
        </motion.p>

        <motion.h1
          className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-extrabold tracking-[-0.03em] leading-[1.08] mb-6"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3 }}
        >
          Do lead ao cliente.
          <br />
          <span className="text-accent">Automático.</span>
        </motion.h1>

        <motion.p
          className="text-base sm:text-lg text-text-secondary max-w-xl mx-auto mb-10 leading-relaxed"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5 }}
        >
          Encontre negócios, analise sua presença digital, gere landing pages
          personalizadas e envie mensagens — tudo no piloto automático.
        </motion.p>

        <motion.div
          className="flex flex-col sm:flex-row gap-3 justify-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.7 }}
        >
          <a
            href="#agendar"
            className="bg-accent text-bg font-bold text-base rounded-lg px-7 py-3.5 hover:bg-accent-dim transition-colors shadow-[0_0_30px_rgba(52,211,153,0.2)]"
          >
            Agendar Demo
          </a>
          <a
            href="#como-funciona"
            className="border border-border text-text font-medium text-base rounded-lg px-7 py-3.5 hover:bg-surface-raised transition-colors"
          >
            Ver em Ação ↓
          </a>
        </motion.div>
      </div>
    </section>
  );
}
