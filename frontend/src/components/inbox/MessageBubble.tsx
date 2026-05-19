import type { Message } from "@/lib/api-inbox";
import { MessageStatusIcon } from "./MessageStatusIcon";

interface Props {
  message: Message;
}

function fmtTime(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("pt-BR", {
    hour: "2-digit", minute: "2-digit",
  });
}

export function MessageBubble({ message }: Props) {
  const cls = `msg-bubble msg-bubble-${message.direction}`;
  const time = fmtTime(
    message.direction === "in" ? message.received_at : message.sent_at,
  );

  return (
    <div className={cls}>
      <div>{message.body}</div>
      <div className="msg-bubble-meta">
        <span>{time}</span>
        <MessageStatusIcon message={message} />
      </div>
    </div>
  );
}
