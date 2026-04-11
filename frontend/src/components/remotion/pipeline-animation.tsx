import { useCurrentFrame, useVideoConfig, interpolate, spring, Sequence } from "remotion";

function MapPin({ frame, fps, delay }: { frame: number; fps: number; delay: number }) {
  const adjustedFrame = Math.max(0, frame - delay);
  const opacity = spring({ frame: adjustedFrame, fps, config: { damping: 15 } });
  const scale = interpolate(opacity, [0, 1], [0, 1]);
  return (
    <div style={{ opacity, transform: `scale(${scale})` }}>
      <div
        style={{
          width: 12,
          height: 12,
          borderRadius: "50%",
          background: "#34d399",
          boxShadow: "0 0 12px rgba(52,211,153,0.5)",
        }}
      />
    </div>
  );
}

function LeadCard({ frame, fps }: { frame: number; fps: number }) {
  const opacity = spring({ frame, fps, config: { damping: 20 } });
  const y = interpolate(opacity, [0, 1], [20, 0]);
  return (
    <div
      style={{
        opacity,
        transform: `translateY(${y}px)`,
        background: "rgba(26,26,29,0.9)",
        border: "1px solid rgba(52,211,153,0.2)",
        borderRadius: 10,
        padding: "12px 16px",
        width: 220,
        backdropFilter: "blur(8px)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
        <span style={{ color: "#f0f0f3", fontSize: 13, fontWeight: 600 }}>Padaria Dona Maria</span>
        <span style={{ color: "#34d399", fontSize: 11, fontWeight: 700, background: "rgba(52,211,153,0.1)", padding: "2px 8px", borderRadius: 8 }}>87</span>
      </div>
      <span style={{ color: "rgba(255,255,255,0.35)", fontSize: 11 }}>Sem SSL · Site não responsivo</span>
    </div>
  );
}

function LPPreview({ frame, fps }: { frame: number; fps: number }) {
  const opacity = spring({ frame, fps, config: { damping: 20 } });
  const scale = interpolate(opacity, [0, 1], [0.9, 1]);
  return (
    <div
      style={{
        opacity,
        transform: `scale(${scale})`,
        background: "rgba(26,26,29,0.9)",
        border: "1px solid rgba(52,211,153,0.15)",
        borderRadius: 10,
        padding: 12,
        width: 180,
        backdropFilter: "blur(8px)",
      }}
    >
      <div style={{ background: "rgba(52,211,153,0.05)", borderRadius: 6, height: 80, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 8 }}>
        <span style={{ color: "rgba(52,211,153,0.4)", fontSize: 10, textTransform: "uppercase", letterSpacing: 2 }}>LP Preview</span>
      </div>
      <div style={{ height: 4, background: "rgba(52,211,153,0.2)", borderRadius: 2, width: "70%", marginBottom: 4 }} />
      <div style={{ height: 4, background: "rgba(255,255,255,0.05)", borderRadius: 2, width: "90%" }} />
    </div>
  );
}

function WhatsAppBubble({ frame, fps }: { frame: number; fps: number }) {
  const opacity = spring({ frame, fps, config: { damping: 20 } });
  const x = interpolate(opacity, [0, 1], [30, 0]);
  return (
    <div
      style={{
        opacity,
        transform: `translateX(${x}px)`,
        background: "rgba(52,211,153,0.1)",
        border: "1px solid rgba(52,211,153,0.2)",
        borderRadius: "12px 12px 12px 2px",
        padding: "10px 14px",
        maxWidth: 240,
        backdropFilter: "blur(8px)",
      }}
    >
      <span style={{ color: "#f0f0f3", fontSize: 12, lineHeight: 1.5 }}>
        Olá! Vi que o site da Padaria Dona Maria pode melhorar...
      </span>
    </div>
  );
}

export function PipelineAnimation() {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const segmentDuration = Math.floor(durationInFrames / 4);

  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
      {/* Stage 1: Map pins */}
      <Sequence from={0} durationInFrames={segmentDuration}>
        <div style={{ position: "absolute", top: "35%", left: "15%" }}>
          <MapPin frame={frame} fps={fps} delay={0} />
        </div>
        <div style={{ position: "absolute", top: "25%", left: "45%" }}>
          <MapPin frame={frame} fps={fps} delay={8} />
        </div>
        <div style={{ position: "absolute", top: "50%", left: "65%" }}>
          <MapPin frame={frame} fps={fps} delay={16} />
        </div>
      </Sequence>

      {/* Stage 2: Lead card */}
      <Sequence from={segmentDuration} durationInFrames={segmentDuration}>
        <div style={{ position: "absolute", top: "30%", left: "50%", transform: "translateX(-50%)" }}>
          <LeadCard frame={frame - segmentDuration} fps={fps} />
        </div>
      </Sequence>

      {/* Stage 3: LP preview */}
      <Sequence from={segmentDuration * 2} durationInFrames={segmentDuration}>
        <div style={{ position: "absolute", top: "28%", left: "50%", transform: "translateX(-50%)" }}>
          <LPPreview frame={frame - segmentDuration * 2} fps={fps} />
        </div>
      </Sequence>

      {/* Stage 4: WhatsApp bubble */}
      <Sequence from={segmentDuration * 3} durationInFrames={segmentDuration}>
        <div style={{ position: "absolute", top: "35%", left: "50%", transform: "translateX(-50%)" }}>
          <WhatsAppBubble frame={frame - segmentDuration * 3} fps={fps} />
        </div>
      </Sequence>
    </div>
  );
}
