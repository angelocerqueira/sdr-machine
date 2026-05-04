"use client";

import { motion } from "framer-motion";
import { useFadeUpOnView, lpDuration, lpEase } from "./lp-motion";

const TOOLS = ["Apollo", "Lusha", "ChatGPT", "Mailshake", "Carrd"];

export function StackSubstitutes() {
  const { ref, visible } = useFadeUpOnView<HTMLDivElement>(0.2);
  return (
    <section ref={ref} className="py-24 px-6" style={{ background: "var(--paper-0)" }}>
      <div className="mx-auto max-w-4xl text-center">
        <h2
          className="font-sans mb-12"
          style={{ color: "var(--ink-0)", fontSize: "clamp(28px, 4.5vw, 44px)", letterSpacing: "-0.025em", lineHeight: 1.1, fontWeight: 480 }}
        >
          Hoje, a mesma entrega
          <br />
          usa 5 ferramentas.
        </h2>

        <div className="flex flex-wrap justify-center gap-4 mb-10">
          {TOOLS.map((tool, i) => (
            <motion.div
              key={tool}
              initial={{ opacity: 0, y: 8 }}
              animate={visible ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: lpDuration.base, ease: lpEase, delay: i * 0.08 }}
              className="relative rounded-md px-6 py-4"
              style={{ border: "1px solid var(--line-2)", background: "var(--paper-1)", minWidth: "140px" }}
            >
              <div style={{ color: "var(--ink-3)", fontWeight: 500, filter: "grayscale(1)" }}>
                {tool}
              </div>
              <motion.div
                initial={{ scale: 1.4, opacity: 0 }}
                animate={visible ? { scale: 1, opacity: 1 } : {}}
                transition={{ duration: 0.3, ease: lpEase, delay: 0.4 + i * 0.08 }}
                className="absolute inset-0 grid place-items-center pointer-events-none"
              >
                <span
                  style={{ color: "var(--danger)", fontSize: "32px", fontWeight: 700, transform: "rotate(-8deg)" }}
                >
                  ✕
                </span>
              </motion.div>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={visible ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: lpDuration.slow, ease: lpEase, delay: 0.9 }}
          className="flex flex-col items-center gap-6"
        >
          <div style={{ color: "var(--ink-3)", fontSize: "24px" }}>↓</div>
          <div
            className="rounded-lg px-8 py-5"
            style={{
              border: "1px solid var(--line-3)",
              background: "var(--paper-1)",
              boxShadow: "0 0 40px color-mix(in oklch, var(--accent) 15%, transparent)",
            }}
          >
            <div className="font-sans tracking-tight" style={{ color: "var(--ink-0)", fontSize: "20px", fontWeight: 600 }}>SDR Machine</div>
          </div>
          <div
            className="font-mono mt-4"
            style={{ color: "var(--ink-3)", fontSize: "11px", letterSpacing: "0.05em" }}
          >
            + 8h/dia de SDR consolidando manualmente.
          </div>
        </motion.div>
      </div>
    </section>
  );
}
