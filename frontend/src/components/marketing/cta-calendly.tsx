"use client";

import { useEffect } from "react";
import { motion } from "framer-motion";
import { useFadeUpOnView, lpDuration, lpEase } from "./lp-motion";

export function CtaCalendly() {
  const { ref, visible } = useFadeUpOnView<HTMLDivElement>(0.15);
  const calendlyUrl = process.env.NEXT_PUBLIC_CALENDLY_URL;

  useEffect(() => {
    if (!calendlyUrl) return;
    const script = document.createElement("script");
    script.src = "https://assets.calendly.com/assets/external/widget.js";
    script.async = true;
    document.body.appendChild(script);
    return () => {
      document.body.removeChild(script);
    };
  }, [calendlyUrl]);

  return (
    <section
      id="agendar"
      ref={ref}
      className="py-24 px-6 relative overflow-hidden"
      style={{ background: "var(--paper-1)" }}
    >
      {/* Astrolábio reduzido como decoração */}
      <div className="absolute right-[-60px] top-1/2 -translate-y-1/2 w-[280px] h-[280px] opacity-20 pointer-events-none hidden lg:block">
        <svg viewBox="0 0 380 380" fill="none">
          <circle cx="190" cy="190" r="180" stroke="var(--warn)" strokeWidth="0.5" opacity="0.5" />
          <circle cx="190" cy="190" r="148" stroke="var(--ink-2)" strokeOpacity="0.3" strokeWidth="1" />
          <circle cx="190" cy="190" r="120" stroke="var(--warn)" strokeWidth="0.8" strokeDasharray="2 6" opacity="0.7" />
          <circle cx="190" cy="190" r="92" stroke="var(--ink-2)" strokeOpacity="0.3" strokeWidth="1" />
          <circle cx="190" cy="190" r="6" fill="var(--accent)" />
        </svg>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={visible ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: lpDuration.slow, ease: lpEase }}
        className="relative mx-auto max-w-3xl text-center"
      >
        <h2
          className="font-sans mb-4"
          style={{ color: "var(--ink-0)", fontSize: "clamp(28px, 4.5vw, 44px)", letterSpacing: "-0.025em", lineHeight: 1.1, fontWeight: 480 }}
        >
          Pronto pra parar de pagar
          <br />
          SDR pra abrir LinkedIn?
        </h2>
        <p style={{ color: "var(--ink-2)", fontSize: "15px", lineHeight: 1.55, marginBottom: "40px" }}>
          15 min de demo. Roda na sua base. Sem compromisso.
        </p>

        {calendlyUrl ? (
          <div
            className="calendly-inline-widget rounded-lg overflow-hidden"
            data-url={calendlyUrl}
            style={{ minWidth: "320px", height: "640px", border: "1px solid var(--line-2)", background: "var(--paper-0)" }}
          />
        ) : (
          <div
            className="rounded-lg p-12"
            style={{ border: "1px solid var(--line-2)", background: "var(--paper-0)", color: "var(--ink-3)" }}
          >
            Calendly ainda não configurado. Defina <code className="font-mono">NEXT_PUBLIC_CALENDLY_URL</code>.
          </div>
        )}

        <div
          className="font-mono mt-6"
          style={{ color: "var(--ink-3)", fontSize: "11px", letterSpacing: "0.05em" }}
        >
          Resposta em &lt;2h
        </div>
      </motion.div>
    </section>
  );
}
