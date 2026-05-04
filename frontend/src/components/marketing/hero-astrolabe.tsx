"use client";

import { motion } from "framer-motion";
import styles from "./hero-astrolabe.module.css";
import { lpDuration, lpEase } from "./lp-motion";

const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  visible: { opacity: 1, y: 0 },
};

export function HeroAstrolabe() {
  return (
    <section className={styles.heroRoot} aria-label="Hero">
      <div className={styles.grain} aria-hidden />
      <div className={styles.body}>
        <motion.div
          initial="hidden"
          animate="visible"
          transition={{ staggerChildren: 0.08, delayChildren: 0.1 }}
        >
          <motion.div
            variants={fadeUp}
            transition={{ duration: lpDuration.base, ease: lpEase }}
            className={styles.eyebrow}
          >
            PARA TIMES B2B QUE PROSPECTAM EM ESCALA
          </motion.div>

          <motion.h1
            variants={fadeUp}
            transition={{ duration: lpDuration.slow, ease: lpEase }}
            className={styles.h1}
          >
            Pare de pagar SDR pra abrir LinkedIn.
          </motion.h1>

          <motion.p
            variants={fadeUp}
            transition={{ duration: lpDuration.base, ease: lpEase }}
            className={styles.sub}
          >
            SDR Machine acha o lead, lê o que existe sobre ele, prepara a abordagem e
            abre a conversa. Você define o canal e o material.
          </motion.p>

          <motion.div
            variants={fadeUp}
            transition={{ duration: lpDuration.base, ease: lpEase }}
            className={styles.ctas}
          >
            <a href="#agendar" className={styles.btnPri}>
              Agendar demo
            </a>
            <a href="#como-funciona" className={styles.btnSec}>
              Ver em ação ↓
            </a>
          </motion.div>

          <motion.div
            variants={fadeUp}
            transition={{ duration: lpDuration.base, ease: lpEase }}
            className={styles.micro}
          >
            500 leads/h · enriquecimento + abordagem prontos
          </motion.div>
        </motion.div>

        <motion.div
          className={styles.astrolabeWrap}
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.2, ease: lpEase, delay: 0.4 }}
        >
          <Astrolabe />
          <div className={styles.centerLabel}>
            OPORTUNIDADE TOPO
            <b>87</b>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function Astrolabe() {
  return (
    <svg viewBox="0 0 380 380" fill="none" aria-hidden>
      {/* Anel externo */}
      <circle cx="190" cy="190" r="180" stroke="var(--warn)" strokeWidth="0.5" opacity="0.35" />
      <circle cx="190" cy="190" r="178" stroke="var(--ink-2)" strokeOpacity="0.18" strokeWidth="1" />

      {/* Ticks cardeais + ordinais */}
      <g stroke="var(--ink-2)" strokeOpacity="0.4" strokeWidth="0.8">
        <line x1="190" y1="10" x2="190" y2="22" />
        <line x1="190" y1="358" x2="190" y2="370" />
        <line x1="10" y1="190" x2="22" y2="190" />
        <line x1="358" y1="190" x2="370" y2="190" />
      </g>
      <g stroke="var(--ink-2)" strokeOpacity="0.22" strokeWidth="0.8">
        <line x1="65" y1="65" x2="73" y2="73" />
        <line x1="307" y1="73" x2="315" y2="65" />
        <line x1="65" y1="315" x2="73" y2="307" />
        <line x1="307" y1="307" x2="315" y2="315" />
      </g>

      {/* Anéis intermediários */}
      <circle cx="190" cy="190" r="148" stroke="var(--ink-2)" strokeOpacity="0.14" strokeWidth="1" />
      <g className={styles.ringRotate}>
        <circle cx="190" cy="190" r="120" stroke="var(--warn)" strokeWidth="0.8" strokeDasharray="2 6" opacity="0.55" />
      </g>
      <circle cx="190" cy="190" r="92" stroke="var(--ink-2)" strokeOpacity="0.16" strokeWidth="1" />

      {/* Crosshair */}
      <line x1="190" y1="42" x2="190" y2="338" stroke="var(--ink-2)" strokeOpacity="0.06" strokeWidth="0.8" />
      <line x1="42" y1="190" x2="338" y2="190" stroke="var(--ink-2)" strokeOpacity="0.06" strokeWidth="0.8" />
      <line x1="80" y1="80" x2="300" y2="300" stroke="var(--ink-2)" strokeOpacity="0.04" strokeWidth="0.6" strokeDasharray="2 5" />
      <line x1="300" y1="80" x2="80" y2="300" stroke="var(--ink-2)" strokeOpacity="0.04" strokeWidth="0.6" strokeDasharray="2 5" />

      {/* Pontos plotados */}
      <g>
        <circle cx="265" cy="115" r="5" fill="var(--danger)" className={styles.dotPulse} />
        <circle cx="265" cy="115" r="11" fill="none" stroke="var(--danger)" strokeWidth="0.8" opacity="0.4" />
        <text x="278" y="113" fontFamily="var(--font-mono)" fontSize="9" fill="var(--ink-3)" letterSpacing="1">87</text>

        <circle cx="295" cy="220" r="4.5" fill="var(--danger)" className={styles.dotPulse} />
        <text x="306" y="223" fontFamily="var(--font-mono)" fontSize="9" fill="var(--ink-3)" letterSpacing="1">92</text>

        <circle cx="120" cy="265" r="4" fill="var(--warn)" />
        <text x="98" y="282" fontFamily="var(--font-mono)" fontSize="9" fill="var(--ink-3)" letterSpacing="1">71</text>

        <circle cx="105" cy="125" r="3.5" fill="var(--ok)" />
        <text x="80" y="115" fontFamily="var(--font-mono)" fontSize="9" fill="var(--ink-4)" letterSpacing="1">48</text>

        {/* Centro azul */}
        <circle cx="190" cy="190" r="6" fill="var(--accent)" />
        <circle cx="190" cy="190" r="14" fill="none" stroke="var(--accent)" strokeWidth="0.8" className={styles.haloBreath} />
      </g>
    </svg>
  );
}
