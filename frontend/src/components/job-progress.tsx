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

  const statusColor = status === "done" ? "text-green-400" : status === "error" ? "text-red-400" : "text-blue-400";

  return (
    <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-4 mt-4">
      <div className="flex items-center gap-2 mb-2">
        <span className={`text-sm font-medium ${statusColor}`}>
          {status === "running" ? "Executando..." : status === "done" ? "Concluído" : "Erro"}
        </span>
      </div>
      <div className="text-xs text-zinc-400 space-y-1 max-h-40 overflow-y-auto">
        {messages.map((msg, i) => (
          <p key={i}>{msg}</p>
        ))}
      </div>
    </div>
  );
}
