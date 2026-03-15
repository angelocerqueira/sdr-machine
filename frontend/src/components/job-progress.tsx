"use client";

import { useEffect, useState, useRef } from "react";
import { streamJob } from "@/lib/api";

interface JobProgressProps {
  jobId: number;
  onDone?: () => void;
}

export function JobProgress({ jobId, onDone }: JobProgressProps) {
  const [messages, setMessages] = useState<string[]>([]);
  const [status, setStatus] = useState<"running" | "done" | "error">("running");
  const onDoneRef = useRef(onDone);
  const scrollRef = useRef<HTMLDivElement>(null);
  onDoneRef.current = onDone;

  useEffect(() => {
    const cleanup = streamJob(jobId, (event) => {
      setMessages((prev) => [...prev, event.message]);
      if (event.type === "done") {
        setStatus("done");
        onDoneRef.current?.();
      }
      if (event.type === "error") setStatus("error");
    });
    return cleanup;
  }, [jobId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const statusConfig = {
    running: { label: "Executando", color: "text-info", dot: "bg-info animate-pulse" },
    done: { label: "Concluído", color: "text-accent", dot: "bg-accent" },
    error: { label: "Erro", color: "text-danger", dot: "bg-danger" },
  };

  const { label, color, dot } = statusConfig[status];

  return (
    <div className="rounded-lg border border-border bg-surface-raised mt-4 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2.5 px-4 py-2.5 border-b border-border-subtle">
        <span className={`w-2 h-2 rounded-full ${dot}`} />
        <span className={`text-xs font-medium font-[family-name:var(--font-mono)] ${color}`}>
          {label}
        </span>
        <span className="text-[10px] text-text-muted font-[family-name:var(--font-mono)] ml-auto">
          Job #{jobId}
        </span>
      </div>

      {/* Log output */}
      <div ref={scrollRef} className="text-xs text-text-muted font-[family-name:var(--font-mono)] p-4 space-y-1 max-h-40 overflow-y-auto bg-bg/50">
        {messages.map((msg, i) => (
          <p key={i} className="leading-relaxed">
            <span className="text-text-muted/50 mr-2 select-none">{String(i + 1).padStart(2, "0")}</span>
            {msg}
          </p>
        ))}
      </div>
    </div>
  );
}
