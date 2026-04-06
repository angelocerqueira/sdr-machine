"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { getLeadLpUrlByPublicId } from "@/lib/api";

type ViewMode = "desktop" | "mobile";

interface LpPreviewProps {
  publicId: string;
  leadName: string;
}

export function LpPreview({ publicId, leadName }: LpPreviewProps) {
  const router = useRouter();
  const [mode, setMode] = useState<ViewMode>("desktop");
  const lpUrl = getLeadLpUrlByPublicId(publicId);

  return (
    <div className="flex flex-col h-screen bg-bg">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-2.5 bg-surface border-b border-border shrink-0">
        <button
          onClick={() => window.history.length > 1 ? router.back() : router.push("/kanban")}
          className="flex items-center gap-1.5 text-text-muted hover:text-text text-[13px] transition-colors"
        >
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="w-4 h-4">
            <path d="M10 3L5 8l5 5" />
          </svg>
          Voltar
        </button>

        <h1 className="text-[13px] font-semibold text-text font-[family-name:var(--font-heading)] truncate max-w-[300px]">
          {leadName}
        </h1>

        <div className="flex items-center gap-1 bg-surface-raised rounded-lg p-0.5 border border-border">
          <button
            onClick={() => setMode("desktop")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[12px] font-medium transition-colors ${
              mode === "desktop"
                ? "bg-accent text-bg"
                : "text-text-muted hover:text-text"
            }`}
          >
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" className="w-3.5 h-3.5">
              <rect x="1" y="2" width="14" height="10" rx="1.5" />
              <path d="M5 14h6M8 12v2" />
            </svg>
            Desktop
          </button>
          <button
            onClick={() => setMode("mobile")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[12px] font-medium transition-colors ${
              mode === "mobile"
                ? "bg-accent text-bg"
                : "text-text-muted hover:text-text"
            }`}
          >
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" className="w-3.5 h-3.5">
              <rect x="4" y="1" width="8" height="14" rx="1.5" />
              <path d="M7 12.5h2" />
            </svg>
            Mobile
          </button>
        </div>
      </header>

      {/* Preview area */}
      {mode === "desktop" ? (
        <iframe
          src={lpUrl}
          className="flex-1 w-full bg-white"
          title={`LP Preview — ${leadName}`}
        />
      ) : (
        <div className="flex-1 flex items-center justify-center bg-bg overflow-auto py-6">
          {/* iPhone frame */}
          <div className="relative shrink-0" style={{ width: 395, height: 852 }}>
            {/* Device shell */}
            <div className="absolute inset-0 rounded-[48px] border-[3px] border-[#333] bg-black shadow-2xl overflow-hidden">
              {/* Dynamic Island */}
              <div className="absolute top-3 left-1/2 -translate-x-1/2 w-[120px] h-[34px] bg-black rounded-full z-10" />

              {/* Screen area */}
              <div className="absolute inset-[3px] rounded-[45px] overflow-hidden bg-white">
                <iframe
                  src={lpUrl}
                  className="w-full h-full border-0"
                  style={{ width: 375, height: 812 }}
                  title={`LP Preview Mobile — ${leadName}`}
                />
              </div>

              {/* Home indicator */}
              <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-[134px] h-[5px] bg-[#555] rounded-full z-10" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
