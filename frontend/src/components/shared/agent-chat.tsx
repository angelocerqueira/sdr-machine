"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { AgentChatData, ChatMessage } from "@/lib/practice-types";

// ─── Waveform processing indicator ────────────────────────────────────────────

const WAVEFORM_HEIGHTS = [12, 20, 28, 16, 24, 18, 14];
const WAVEFORM_DELAYS = [0, 0.1, 0.2, 0.05, 0.15, 0.25, 0.08];

function WaveformBars() {
  return (
    <div className="flex items-center gap-[3px]" aria-label="processando">
      {WAVEFORM_HEIGHTS.map((h, i) => (
        <div
          key={i}
          className="w-[3px] rounded-full bg-accent/70"
          style={{
            height: h,
            animation: `waveform-bar 0.8s ease-in-out infinite alternate`,
            animationDelay: `${WAVEFORM_DELAYS[i]}s`,
          }}
        />
      ))}
    </div>
  );
}

function ProcessingIndicator() {
  return (
    <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl border border-border-subtle bg-[rgba(255,255,255,0.03)] w-fit max-w-[200px]">
      <WaveformBars />
      <span
        className="text-[10px] text-text-muted font-[family-name:var(--font-mono)] uppercase tracking-widest"
        style={{ letterSpacing: "0.12em" }}
      >
        processando
      </span>
    </div>
  );
}

// ─── Bot avatar icon ───────────────────────────────────────────────────────────

function BotAvatar({ pulse }: { pulse?: boolean }) {
  return (
    <div className="relative shrink-0">
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center text-bg text-xs font-bold"
        style={{
          background: "linear-gradient(135deg, #34d399 0%, #059669 100%)",
        }}
      >
        IA
      </div>
      {pulse && (
        <span
          className="absolute inset-0 rounded-full border border-accent/50"
          style={{ animation: "pulse-ring 1.8s ease-out infinite" }}
        />
      )}
    </div>
  );
}

// ─── Single message bubble ─────────────────────────────────────────────────────

interface MessageBubbleProps {
  message: ChatMessage;
  /** For bot messages that are still being typewritten */
  displayText?: string;
  showMeta?: boolean;
}

function MessageBubble({ message, displayText, showMeta }: MessageBubbleProps) {
  const text = displayText ?? message.text;
  const isBot = message.role === "bot";

  if (isBot) {
    return (
      <div className="flex items-start gap-2.5 max-w-[85%]">
        <BotAvatar />
        <div>
          <div className="rounded-xl rounded-tl-sm px-3.5 py-2.5 border border-border-subtle bg-[rgba(255,255,255,0.04)]">
            <p className="text-[13px] text-text leading-relaxed">{text}</p>
          </div>
          {showMeta && (
            <div className="flex items-center gap-3 mt-1 px-1">
              <span className="text-[9px] text-text-muted font-[family-name:var(--font-mono)]">
                1.2s de resposta
              </span>
              <span className="w-[1px] h-2 bg-border-subtle" />
              <span className="text-[9px] text-info/60 font-[family-name:var(--font-mono)]">
                Fonte: base de conhecimento
              </span>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-end">
      <div className="rounded-xl rounded-tr-sm px-3.5 py-2.5 max-w-[80%] bg-[rgba(52,211,153,0.08)] border border-accent/15">
        <p className="text-[13px] text-text leading-relaxed">{text}</p>
      </div>
    </div>
  );
}

// ─── Main AgentChat component ──────────────────────────────────────────────────

type DisplayEntry =
  | { kind: "message"; message: ChatMessage; complete: boolean }
  | { kind: "processing" };

const TYPEWRITER_DELAY_MS = 30;
const PROCESSING_DURATION_MS = 1500;

export function AgentChat({
  data,
  active = true,
  embedded = false,
  skipInitialProcessing = false,
}: {
  data: AgentChatData;
  active?: boolean;
  embedded?: boolean;
  skipInitialProcessing?: boolean;
}) {
  const [entries, setEntries] = useState<DisplayEntry[]>([]);
  const [typingText, setTypingText] = useState("");
  const [actionsVisible, setActionsVisible] = useState(false);
  const [usedActions, setUsedActions] = useState<Set<string>>(new Set());
  const [isAnimating, setIsAnimating] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const typingRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  // Auto-scroll to bottom whenever entries or typingText change
  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [entries, typingText]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (typingRef.current) clearTimeout(typingRef.current);
    };
  }, []);

  // Typewriter helper — resolves when done
  const typewrite = useCallback(
    (text: string): Promise<void> => {
      return new Promise((resolve) => {
        let i = 0;
        setTypingText("");

        function tick() {
          if (!mountedRef.current) return;
          i++;
          setTypingText(text.slice(0, i));
          if (i < text.length) {
            typingRef.current = setTimeout(tick, TYPEWRITER_DELAY_MS);
          } else {
            setTypingText("");
            resolve();
          }
        }

        typingRef.current = setTimeout(tick, TYPEWRITER_DELAY_MS);
      });
    },
    []
  );

  // Show processing indicator for PROCESSING_DURATION_MS then resolve
  const showProcessing = useCallback((): Promise<void> => {
    return new Promise((resolve) => {
      if (!mountedRef.current) { resolve(); return; }
      setEntries((prev) => [...prev, { kind: "processing" }]);
      typingRef.current = setTimeout(() => {
        if (!mountedRef.current) { resolve(); return; }
        setEntries((prev) => prev.filter((e) => e.kind !== "processing"));
        resolve();
      }, PROCESSING_DURATION_MS);
    });
  }, []);

  // Play a sequence of ChatMessage[]
  const playSequence = useCallback(
    async (messages: ChatMessage[], opts?: { skipProcessing?: boolean }) => {
      setIsAnimating(true);
      for (const msg of messages) {
        if (!mountedRef.current) break;

        if (msg.role === "bot") {
          if (!opts?.skipProcessing) {
            await showProcessing();
          }
          if (!mountedRef.current) break;

          // Start typewriting — add a temporary in-progress bot entry
          const inProgressEntry: DisplayEntry = {
            kind: "message",
            message: msg,
            complete: false,
          };
          setEntries((prev) => [...prev, inProgressEntry]);

          await typewrite(msg.text);

          if (!mountedRef.current) break;

          // Mark the last entry as complete
          setEntries((prev) => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (updated[lastIdx]?.kind === "message") {
              updated[lastIdx] = { kind: "message", message: msg, complete: true };
            }
            return updated;
          });
        } else {
          // User message — instant
          setEntries((prev) => [
            ...prev,
            { kind: "message", message: msg, complete: true },
          ]);
        }
      }

      if (mountedRef.current) {
        setIsAnimating(false);
      }
    },
    [showProcessing, typewrite]
  );

  // Kick off initial sequence when active
  useEffect(() => {
    if (!active || data.messages.length === 0) return;
    let cancelled = false;

    async function run() {
      await playSequence(data.messages, { skipProcessing: skipInitialProcessing });
      if (!cancelled && mountedRef.current) {
        setActionsVisible(true);
      }
    }

    run();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  const handleAction = useCallback(
    async (action: string) => {
      if (isAnimating || usedActions.has(action)) return;

      setUsedActions((prev) => new Set(prev).add(action));

      const userMsg: ChatMessage = { role: "user", text: action };
      const responseMessages = data.responses[action] ?? [];

      setEntries((prev) => [
        ...prev,
        { kind: "message", message: userMsg, complete: true },
      ]);

      if (responseMessages.length > 0) {
        await playSequence(responseMessages);
      }
    },
    [isAnimating, usedActions, data.responses, playSequence]
  );

  // Determine which entry is currently being typewritten
  const lastEntry = entries[entries.length - 1];
  const isLastEntryIncomplete =
    lastEntry?.kind === "message" && !lastEntry.complete;

  const messagesList = (
    <div
      ref={scrollRef}
      className={
        embedded
          ? "flex flex-col gap-3 px-4 py-4 flex-1 overflow-y-auto"
          : "flex flex-col gap-3 px-4 py-4 overflow-y-auto"
      }
      style={embedded ? undefined : { maxHeight: 380, minHeight: 200 }}
    >
      {entries.map((entry, idx) => {
        if (entry.kind === "processing") {
          return <ProcessingIndicator key={`proc-${idx}`} />;
        }

        const isCurrentlyTyping = idx === entries.length - 1 && isLastEntryIncomplete;

        return (
          <MessageBubble
            key={idx}
            message={entry.message}
            displayText={isCurrentlyTyping ? typingText : undefined}
            showMeta={entry.complete && entry.message.role === "bot"}
          />
        );
      })}
    </div>
  );

  const quickActionsBar = actionsVisible && data.quickActions.length > 0 && (
    <div className="flex flex-wrap gap-2 px-4 pb-4 pt-3 border-t border-[rgba(255,255,255,0.06)] shrink-0">
      {data.quickActions.map((action) => {
        const used = usedActions.has(action);
        return (
          <button
            key={action}
            onClick={() => handleAction(action)}
            disabled={used || isAnimating}
            className={[
              "px-3 py-1.5 rounded-full text-[11px] font-medium border transition-all duration-150",
              "font-[family-name:var(--font-mono)] uppercase tracking-wide",
              used || isAnimating
                ? "border-border-subtle text-text-muted opacity-40 cursor-not-allowed"
                : "border-accent/30 text-accent bg-accent-subtle hover:bg-[rgba(52,211,153,0.12)] hover:border-accent/50 cursor-pointer",
            ].join(" ")}
          >
            {action}
          </button>
        );
      })}
    </div>
  );

  const sharedStyles = (
    <style>{`
      @keyframes waveform-bar {
        from { transform: scaleY(0.4); opacity: 0.5; }
        to   { transform: scaleY(1);   opacity: 1;   }
      }
      @keyframes pulse-ring {
        0%   { transform: scale(1);   opacity: 0.6; }
        100% { transform: scale(1.6); opacity: 0;   }
      }
      @keyframes online-pulse {
        0%, 100% { opacity: 1; }
        50%       { opacity: 0.4; }
      }
    `}</style>
  );

  if (embedded) {
    return (
      <>
        {sharedStyles}
        <div className="flex flex-col h-full min-h-0">
          {messagesList}
          {quickActionsBar}
        </div>
      </>
    );
  }

  return (
    <>
      {sharedStyles}

      <div className="flex flex-col items-center gap-4 w-full">
        {/* Chat container */}
        <div
          className="w-full max-w-3xl lg:max-w-[60%] mx-auto rounded-2xl border border-[rgba(255,255,255,0.07)] overflow-hidden"
          style={{
            background: "rgba(255,255,255,0.03)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
          }}
        >
          {/* Header */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-[rgba(255,255,255,0.06)]">
            <BotAvatar pulse />
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-semibold text-text truncate">
                {data.businessName}
              </p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span
                  className="w-1.5 h-1.5 rounded-full bg-accent"
                  style={{ animation: "online-pulse 2s ease-in-out infinite" }}
                />
                <span className="text-[10px] text-accent font-[family-name:var(--font-mono)] uppercase tracking-widest">
                  Online agora
                </span>
              </div>
            </div>
            {/* Three-dot controls — purely decorative */}
            <div className="flex items-center gap-1.5">
              {[0, 0.08, 0.16].map((_, i) => (
                <span
                  key={i}
                  className="w-1.5 h-1.5 rounded-full bg-border"
                  style={{ opacity: 1 - i * 0.2 }}
                />
              ))}
            </div>
          </div>

          {messagesList}
          {quickActionsBar}
        </div>

        {/* Badge */}
        <p className="text-[10px] font-[family-name:var(--font-mono)] text-text-muted uppercase tracking-widest">
          Simulacao baseada no perfil: {data.niche}
        </p>
      </div>
    </>
  );
}
