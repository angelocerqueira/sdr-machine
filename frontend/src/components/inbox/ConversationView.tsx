"use client";

import { MessageBubble } from "./MessageBubble";
import { Composer } from "./Composer";
import { ConversationHeader } from "./ConversationHeader";
import { DayDivider } from "./DayDivider";
import { ScrollToBottomFab } from "./ScrollToBottomFab";
import { useGroupedMessages } from "./use-grouped-messages";
import { useAutoScroll } from "./use-auto-scroll";
import type { ConversationDetail } from "@/lib/api-inbox";

interface Props {
  conversation: ConversationDetail;
  onSend: (body: string) => Promise<void>;
}

export function ConversationView({ conversation, onSend }: Props) {
  const items = useGroupedMessages(conversation.messages);
  const { scrollRef, newMessagesCount, scrollToBottom } = useAutoScroll(
    conversation.messages.length,
  );

  return (
    <>
      <ConversationHeader conversation={conversation} />

      <div className="inbox-conv-messages-wrap">
        <div className="inbox-conv-messages" ref={scrollRef}>
          {items.length === 0 ? (
            <div className="inbox-empty">Nenhuma mensagem ainda.</div>
          ) : (
            items.map((it, idx) =>
              it.kind === "divider" ? (
                <DayDivider key={`d-${idx}`} label={it.label} />
              ) : (
                <MessageBubble key={it.message.id} message={it.message} />
              ),
            )
          )}
        </div>
        <ScrollToBottomFab count={newMessagesCount} onClick={() => scrollToBottom(true)} />
      </div>

      <Composer onSend={onSend} />
    </>
  );
}
