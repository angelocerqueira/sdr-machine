"use client";

import { useEffect, useRef } from "react";
import { MessageBubble } from "./MessageBubble";
import { Composer } from "./Composer";
import type { ConversationDetail } from "@/lib/api-inbox";

interface Props {
  conversation: ConversationDetail;
  onSend: (body: string) => Promise<void>;
}

export function ConversationView({ conversation, onSend }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [conversation.messages.length]);

  return (
    <>
      <header style={{
        padding: "12px 16px", borderBottom: "1px solid var(--border)",
        display: "flex", justifyContent: "space-between", alignItems: "center",
      }}>
        <div>
          <strong>{conversation.phone}</strong>
          <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
            {conversation.provider} · {conversation.status}
          </div>
        </div>
      </header>
      <div className="inbox-conv-messages" ref={scrollRef}>
        {conversation.messages.length === 0 ? (
          <div className="inbox-empty">Nenhuma mensagem ainda.</div>
        ) : (
          conversation.messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))
        )}
      </div>
      <Composer onSend={onSend} />
    </>
  );
}
