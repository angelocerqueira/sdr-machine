import { AbsoluteFill } from "remotion";
import { ParticleBackground } from "./particle-background";
import { PipelineAnimation } from "./pipeline-animation";

export function HeroComposition() {
  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a0c" }}>
      <ParticleBackground />
      <PipelineAnimation />
    </AbsoluteFill>
  );
}
