import type { Message } from "@/lib/api-inbox";

interface Props {
  message: Message;
}

function fmtTime(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("pt-BR", {
    hour: "2-digit", minute: "2-digit",
  });
}

function statusGlyph(message: Message): string {
  if (message.direction !== "out") return "";
  if (message.error) return "❌";
  if (message.read_at) return "✓✓";
  if (message.delivered_at) return "✓✓";
  if (message.sent_at) return "✓";
  return "…";
}

export function MessageBubble({ message }: Props) {
  const cls = `msg-bubble msg-bubble-${message.direction}`;
  const time = fmtTime(
    message.direction === "in" ? message.received_at : message.sent_at,
  );
  const glyph = statusGlyph(message);
  const isRead = !!message.read_at;
  const isFailed = !!message.error;

  return (
    <div className={cls}>
      <div>{message.body}</div>
      <div className="msg-bubble-meta">
        <span>{time}</span>
        {glyph && (
          <span
            className={
              isFailed
                ? "msg-status-failed"
                : isRead
                  ? "msg-status-read"
                  : ""
            }
            aria-label={
              isFailed
                ? "falha no envio"
                : isRead
                  ? "lida"
                  : "enviada"
            }
          >
            {glyph}
          </span>
        )}
      </div>
    </div>
  );
}
