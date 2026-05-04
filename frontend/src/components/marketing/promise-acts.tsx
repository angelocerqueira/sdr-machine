"use client";

import { motion } from "framer-motion";
import { useFadeUpOnView, lpDuration, lpEase } from "./lp-motion";
import { MockupAcha, MockupEntende, MockupPrepara, MockupAbre } from "./promise-mockups";

type Act = {
  num: string;
  verb: string;
  h3: string;
  sub: string;
  bullets: string[];
  Mockup: React.ComponentType;
};

const ACTS: Act[] = [
  {
    num: "01",
    verb: "ACHA",
    h3: "Onde seu cliente está. E quem é ele.",
    sub: "Pesquisa em Google Maps, Apollo e sua base. Encontra empresas que batem com seu ICP, deduplica, valida CNPJ e enriquece contatos.",
    bullets: ["Filtro nicho × cidade", "Deduplicação automática", "CNPJ + razão social validados"],
    Mockup: MockupAcha,
  },
  {
    num: "02",
    verb: "ENTENDE",
    h3: "Lê o site. Abre a stack. Entende a dor real.",
    sub: "Crawl do site, schema.org, tech stack, reviews do Google. Calcula um score 0-100 com 10+ sinais. Você sabe o que dói antes de falar.",
    bullets: ["10+ sinais (SSL, mobile, stack, reviews)", "Score 0-100 explicável", "Reasons em texto pronto"],
    Mockup: MockupEntende,
  },
  {
    num: "03",
    verb: "PREPARA",
    h3: "Material certo. Pra esse lead. Em segundos.",
    sub: "Gera o asset de abordagem que faz sentido pro lead — landing page personalizada, infográfico de diagnóstico, mockup. Tudo público, sem login, pronto pra enviar.",
    bullets: ["Templates conectados ao diagnóstico", "LP, infográfico ou mockup", "URL pública dedicada"],
    Mockup: MockupPrepara,
  },
  {
    num: "04",
    verb: "ABRE",
    h3: "Mensagem pronta. No canal certo. Em pt-BR humano.",
    sub: "Compõe abordagem inicial, follow-up de 48h e mensagem final. Link wa.me pré-preenchido. Tom configurável (formal, parceiro, direto).",
    bullets: ["3 cadências por lead", "WhatsApp, e-mail, ligação", "Tom configurável"],
    Mockup: MockupAbre,
  },
];

export function PromiseActs() {
  return (
    <section id="como-funciona" className="py-16" style={{ background: "var(--paper-0)" }}>
      {ACTS.map((act, i) => (
        <ActRow key={act.num} act={act} reverse={i % 2 === 1} />
      ))}
    </section>
  );
}

function ActRow({ act, reverse }: { act: Act; reverse: boolean }) {
  const { ref, visible } = useFadeUpOnView<HTMLDivElement>(0.15);
  const Mockup = act.Mockup;
  const reverseClass = reverse ? "lg:[&>*:first-child]:order-2" : "";
  return (
    <div ref={ref} className="mx-auto max-w-6xl px-6 py-16 lg:py-24">
      <div className={`grid gap-10 lg:gap-16 items-center lg:grid-cols-2 ${reverseClass}`}>
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={visible ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: lpDuration.slow, ease: lpEase }}
        >
          <div
            className="font-mono mb-4 inline-flex items-center gap-2"
            style={{ color: "var(--warn)", fontSize: "10px", letterSpacing: "0.18em", textTransform: "uppercase" }}
          >
            <span style={{ width: "16px", height: "1px", background: "var(--warn)" }} />
            {act.num} · {act.verb}
          </div>
          <h3
            className="font-sans mb-4"
            style={{ color: "var(--ink-0)", fontSize: "clamp(24px, 3.5vw, 36px)", letterSpacing: "-0.025em", lineHeight: 1.1, fontWeight: 480 }}
          >
            {act.h3}
          </h3>
          <p style={{ color: "var(--ink-2)", fontSize: "15px", lineHeight: 1.55, maxWidth: "480px", marginBottom: "24px" }}>
            {act.sub}
          </p>
          <ul className="space-y-2 font-mono" style={{ color: "var(--ink-3)", fontSize: "11px" }}>
            {act.bullets.map((b) => (
              <li key={b} className="flex items-start gap-2">
                <span style={{ color: "var(--warn)", marginTop: "2px" }}>·</span>
                <span>{b}</span>
              </li>
            ))}
          </ul>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={visible ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: lpDuration.slow, ease: lpEase, delay: 0.1 }}
        >
          <Mockup />
        </motion.div>
      </div>
    </div>
  );
}
