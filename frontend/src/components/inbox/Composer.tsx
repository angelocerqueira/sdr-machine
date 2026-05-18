"use client";

import { useState, useRef, type KeyboardEvent } from "react";

interface Props {
  onSend: (body: string) => Promise<void>;
  disabled?: boolean;
}

export function Composer({ onSend, disabled }: Props) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);

  async function handleSend() {
    const trimmed = text.trim();
    if (!trimmed || sending || disabled) return;
    setSending(true);
    try {
      await onSend(trimmed);
      setText("");
      ref.current?.focus();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Erro ao enviar");
    } finally {
      setSending(false);
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="composer">
      <textarea
        ref={ref}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Mensagem..."
        className="composer-textarea"
        disabled={disabled || sending}
        rows={1}
      />
      <button
        type="button"
        className="composer-send"
        onClick={handleSend}
        disabled={disabled || sending || !text.trim()}
      >
        {sending ? "Enviando…" : "Enviar"}
      </button>
    </div>
  );
}
