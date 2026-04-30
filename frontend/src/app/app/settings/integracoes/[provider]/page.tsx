"use client";
import { use } from "react";

export default function IntegrationDetail({ params }: { params: Promise<{ provider: string }> }) {
  const { provider } = use(params);
  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 480 }}>{provider}</h2>
      <p style={{ color: "var(--text-muted)" }}>Em construção.</p>
    </div>
  );
}
