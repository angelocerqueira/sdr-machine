import { HeroSection } from "@/components/marketing/hero-section";
import { BeforeAfter } from "@/components/marketing/before-after";
import { PipelineSection } from "@/components/marketing/pipeline-section";
import { FeaturesGrid } from "@/components/marketing/features-grid";
import { CTASection } from "@/components/marketing/cta-section";
import { MarketingFooter } from "@/components/marketing/marketing-footer";

export default function LandingPage() {
  return (
    <main>
      <HeroSection />
      <BeforeAfter />
      <PipelineSection />
      <FeaturesGrid />
      <CTASection />
      <MarketingFooter />
    </main>
  );
}
