import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";

interface Particle {
  x: number;
  y: number;
  size: number;
  speed: number;
  opacity: number;
}

const PARTICLES: Particle[] = Array.from({ length: 30 }, (_, i) => ({
  x: (i * 37 + 13) % 100,
  y: (i * 53 + 7) % 100,
  size: 2 + (i % 3) * 1.5,
  speed: 0.3 + (i % 5) * 0.15,
  opacity: 0.15 + (i % 4) * 0.1,
}));

const CONNECTIONS: [number, number][] = [];
for (let i = 0; i < PARTICLES.length; i++) {
  for (let j = i + 1; j < PARTICLES.length; j++) {
    const dx = PARTICLES[i].x - PARTICLES[j].x;
    const dy = PARTICLES[i].y - PARTICLES[j].y;
    if (Math.sqrt(dx * dx + dy * dy) < 25) {
      CONNECTIONS.push([i, j]);
    }
  }
}

export function ParticleBackground() {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  return (
    <svg width={width} height={height} className="absolute inset-0">
      {/* Grid */}
      <defs>
        <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
          <path d="M 60 0 L 0 0 0 60" fill="none" stroke="rgba(52,211,153,0.04)" strokeWidth="0.5" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid)" />

      {/* Connections */}
      {CONNECTIONS.map(([i, j], idx) => {
        const p1 = PARTICLES[i];
        const p2 = PARTICLES[j];
        const offset1 = Math.sin(frame * 0.01 * p1.speed) * 2;
        const offset2 = Math.sin(frame * 0.01 * p2.speed + 1) * 2;
        const lineOpacity = interpolate(
          Math.sin(frame * 0.02 + idx),
          [-1, 1],
          [0.03, 0.08]
        );
        return (
          <line
            key={`c-${idx}`}
            x1={`${p1.x + offset1}%`}
            y1={`${p1.y + offset1}%`}
            x2={`${p2.x + offset2}%`}
            y2={`${p2.y + offset2}%`}
            stroke="#34d399"
            strokeWidth="0.5"
            opacity={lineOpacity}
          />
        );
      })}

      {/* Particles */}
      {PARTICLES.map((p, i) => {
        const offset = Math.sin(frame * 0.01 * p.speed + i) * 2;
        const pulseOpacity = interpolate(
          Math.sin(frame * 0.03 + i * 0.5),
          [-1, 1],
          [p.opacity * 0.5, p.opacity]
        );
        return (
          <circle
            key={i}
            cx={`${p.x + offset}%`}
            cy={`${p.y + offset}%`}
            r={p.size}
            fill="#34d399"
            opacity={pulseOpacity}
          />
        );
      })}
    </svg>
  );
}
