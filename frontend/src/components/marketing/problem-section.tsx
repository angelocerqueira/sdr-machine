"use client";

import { motion } from "framer-motion";
import { useCountUp, useFadeUpOnView, lpDuration, lpEase } from "./lp-motion";

const CARDS = [
  { value: 8, suffix: "h", label: "ABAS · FERRAMENTAS", text: "40 abas, 12 ferramentas, 0 contexto." },
  { value: 1.2, suffix: "%", label: "RESPOSTA EM MENSAGEM GENÉRICA", text: "“Olá, vi que você é dono de…” — copy que ninguém lê." },
  { value: 0, suffix: "%", label: "CONTEXTO ANTES DA CONVERSA", text: "Seu SDR fala antes de saber o que dói. O cliente sente." },
];

export function ProblemSection() {
  const { ref, visible } = useFadeUpOnView<HTMLDivElement>();

  return (
    <section className="relative py-24 px-6" style={{ background: "var(--paper-0)" }}>
      <div ref={ref} className="mx-auto max-w-5xl text-center">
        <motion.h2
          initial={{ opacity: 0, y: 18 }}
          animate={visible ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: lpDuration.slow, ease: lpEase }}
          style={{ color: "var(--ink-0)", fontSize: "clamp(28px, 4.5vw, 44px)", letterSpacing: "-0.025em", lineHeight: 1.05, fontWeight: 480 }}
          className="font-sans mb-16"
        >
          Hoje você paga 8 horas de SDR
          <br />
          pra entregar 2.
        </motion.h2>

        <div className="grid md:grid-cols-3 gap-4">
          {CARDS.map((card, i) => (
            <motion.div
              key={card.label}
              initial={{ opacity: 0, y: 18 }}
              animate={visible ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: lpDuration.base, ease: lpEase, delay: i * 0.06 }}
              className="rounded-lg p-7 text-left"
              style={{ border: "1px solid var(--line-2)", background: "var(--paper-1)" }}
            >
              <ProblemNumber value={card.value} suffix={card.suffix} />
              <div
                className="font-mono mt-1 mb-3"
                style={{ color: "var(--ink-3)", fontSize: "10px", letterSpacing: "0.18em", textTransform: "uppercase" }}
              >
                {card.label}
              </div>
              <p style={{ color: "var(--ink-2)", fontSize: "14px", lineHeight: 1.55 }}>
                {card.text}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ProblemNumber({ value, suffix }: { value: number; suffix: string }) {
  const { ref, value: animated } = useCountUp(value, 800);
  const formatted = Number.isInteger(value) ? Math.round(animated).toString() : animated.toFixed(1);
  return (
    <span
      ref={ref}
      className="font-mono tabular-nums block"
      style={{ color: "var(--warn)", fontSize: "96px", fontWeight: 600, lineHeight: 0.9, letterSpacing: "-0.03em" }}
    >
      {formatted}
      {suffix}
    </span>
  );
}
