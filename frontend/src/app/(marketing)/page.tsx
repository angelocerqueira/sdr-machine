import { HeroAstrolabe } from "@/components/marketing/hero-astrolabe";
import { ProblemSection } from "@/components/marketing/problem-section";
import { PromiseActs } from "@/components/marketing/promise-acts";
import { PracticeBlock } from "@/components/marketing/practice-block";
import { StackSubstitutes } from "@/components/marketing/stack-substitutes";
import { CtaCalendly } from "@/components/marketing/cta-calendly";
import { MarketingFooter } from "@/components/marketing/marketing-footer";

export default function LandingPage() {
  return (
    <main>
      <HeroAstrolabe />

      {/* SLOT: Trust strip (logos clientes) — ativar quando tiver cases */}
      {/* <TrustStrip /> */}

      <ProblemSection />
      <PromiseActs />
      <PracticeBlock />
      <StackSubstitutes />

      {/* SLOT: Casos / Números — ativar quando tiver quote + métricas */}
      {/* <CasesNumbers /> */}

      <CtaCalendly />
      <MarketingFooter />
    </main>
  );
}
