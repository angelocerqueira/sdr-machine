"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { AgentChatData } from "@/lib/practice-types";
import { AgentChat } from "@/components/shared/agent-chat";

// ─── Close (X) icon ────────────────────────────────────────────────────────────

function CloseIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M12 4L4 12M4 4l8 8"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

// ─── Bot avatar for the bubble ────────────────────────────────────────────────

function BubbleAvatar() {
  return (
    <div
      className="w-full h-full rounded-full flex items-center justify-center text-bg text-sm font-bold relative"
      style={{
        background: "linear-gradient(135deg, #34d399 0%, #059669 100%)",
      }}
    >
      IA
      {/* Pulse ring */}
      <span
        className="absolute inset-0 rounded-full border border-accent/50"
        style={{ animation: "pulse-ring 1.8s ease-out infinite" }}
      />
    </div>
  );
}

// ─── Notification badge ───────────────────────────────────────────────────────

function NotificationBadge() {
  return (
    <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-danger flex items-center justify-center z-10">
      <span className="text-[9px] font-bold text-white leading-none">1</span>
    </span>
  );
}

// ─── Main ChatWidget component ────────────────────────────────────────────────

export function ChatWidget({ data }: { data: AgentChatData }) {
  const [isOpen, setIsOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;

    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [isOpen]);

  return (
    <>
      {/* Shared keyframes — reuse pulse-ring from agent-chat if already injected */}
      <style>{`
        @keyframes pulse-ring {
          0%   { transform: scale(1);   opacity: 0.6; }
          100% { transform: scale(1.6); opacity: 0;   }
        }
      `}</style>

      {/* Wrapper anchored to bottom-right */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
        <AnimatePresence mode="wait">
          {isOpen ? (
            /* ── Open panel ──────────────────────────────────────────────── */
            <motion.div
              key="panel"
              ref={panelRef}
              initial={{ opacity: 0, scale: 0.9, y: 16 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 16 }}
              transition={{ type: "spring", damping: 22, stiffness: 280 }}
              className="flex flex-col overflow-hidden"
              style={{
                width: "min(380px, calc(100vw - 2rem))",
                maxHeight: "min(500px, 70vh)",
                borderRadius: 16,
                background: "rgba(17,17,19,0.95)",
                backdropFilter: "blur(24px)",
                WebkitBackdropFilter: "blur(24px)",
                border: "1px solid rgba(255,255,255,0.08)",
                boxShadow:
                  "0 32px 64px -12px rgba(0,0,0,0.7), 0 8px 24px -4px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.04)",
              }}
            >
              {/* Header */}
              <div
                className="flex items-center gap-3 px-4 py-3 shrink-0"
                style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}
              >
                {/* Mini avatar */}
                <div
                  className="w-8 h-8 rounded-full shrink-0 flex items-center justify-center text-bg text-xs font-bold"
                  style={{
                    background:
                      "linear-gradient(135deg, #34d399 0%, #059669 100%)",
                  }}
                >
                  IA
                </div>

                {/* Business name */}
                <p className="flex-1 min-w-0 text-[13px] font-semibold text-text truncate">
                  {data.businessName}
                </p>

                {/* Close button */}
                <button
                  onClick={() => setIsOpen(false)}
                  className="w-7 h-7 rounded-full flex items-center justify-center text-text-muted hover:text-text hover:bg-[rgba(255,255,255,0.06)] transition-colors cursor-pointer"
                  aria-label="Fechar chat"
                >
                  <CloseIcon />
                </button>
              </div>

              {/* Body — AgentChat fills remaining space */}
              <div className="flex-1 overflow-hidden">
                <div className="h-full overflow-y-auto">
                  <AgentChat data={data} active />
                </div>
              </div>
            </motion.div>
          ) : (
            /* ── Closed bubble ───────────────────────────────────────────── */
            <motion.button
              key="bubble"
              initial={{ opacity: 0, y: 100, scale: 0.8 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.8 }}
              transition={{ delay: 4, type: "spring", damping: 20 }}
              onClick={() => setIsOpen(true)}
              className="relative w-14 h-14 rounded-full cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              aria-label="Abrir chat"
            >
              <BubbleAvatar />
              <NotificationBadge />
            </motion.button>
          )}
        </AnimatePresence>
      </div>
    </>
  );
}
