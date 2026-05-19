import type { Message } from "@/lib/api-inbox";

interface Props {
  message: Message;
}

export function MessageStatusIcon({ message }: Props) {
  if (message.direction !== "out") return null;

  if (message.error) {
    return (
      <span
        className="msg-status msg-status-failed"
        title={message.error}
        aria-label={`falha: ${message.error}`}
      >
        !
      </span>
    );
  }

  if (message.read_at) {
    return (
      <span className="msg-status msg-status-read" aria-label="lida">
        <DoubleCheckIcon />
      </span>
    );
  }

  if (message.delivered_at) {
    return (
      <span className="msg-status msg-status-delivered" aria-label="entregue">
        <DoubleCheckIcon />
      </span>
    );
  }

  if (message.sent_at) {
    return (
      <span className="msg-status msg-status-sent" aria-label="enviada">
        <SingleCheckIcon />
      </span>
    );
  }

  return (
    <span className="msg-status msg-status-queued" aria-label="aguardando">
      …
    </span>
  );
}

function SingleCheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M3 8.5L6.5 12L13 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function DoubleCheckIcon() {
  return (
    <svg width="18" height="14" viewBox="0 0 20 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2 8.5L5 11.5L11 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M8 8.5L11 11.5L17 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
