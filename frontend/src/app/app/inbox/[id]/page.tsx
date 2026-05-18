"use client";

import { useState, useEffect, useRef, use } from "react";
import { useRouter } from "next/navigation";
import useSWR, { mutate } from "swr";
import {
  listConversations, getConversation, sendMessage, markRead,
  type ConversationFilter,
} from "@/lib/api-inbox";
import { InboxList } from "@/components/inbox/InboxList";
import { InboxFilters } from "@/components/inbox/InboxFilters";
import { ConversationView } from "@/components/inbox/ConversationView";
import { ConversationRail } from "@/components/inbox/ConversationRail";
import "@/components/inbox/inbox.css";

export default function InboxDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const conversationId = Number(id);
  const router = useRouter();

  const [filter, setFilter] = useState<ConversationFilter>("all");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const { data: list } = useSWR(
    ["conversations-list", filter, debouncedSearch],
    () => listConversations({ filter, search: debouncedSearch }),
    { refreshInterval: 5000 },
  );

  const { data: conv, error: convError } = useSWR(
    conversationId ? ["conversation", conversationId] : null,
    () => getConversation(conversationId),
    { refreshInterval: 5000 },
  );

  // Auto-mark-read: dispara só na primeira vez que conv carrega com unread > 0.
  // Não re-dispara em re-polls (write-amplification) nem em inbounds subsequentes.
  const markedReadRef = useRef<number | null>(null);
  useEffect(() => {
    if (
      conv &&
      conv.unread_count > 0 &&
      markedReadRef.current !== conv.id
    ) {
      markedReadRef.current = conv.id;
      markRead(conversationId).then(() => {
        mutate(["conversations-list", filter, debouncedSearch]);
      });
    }
  }, [conv, conversationId, filter, debouncedSearch]);

  // Redirect on 404 (must be in effect, not render body)
  useEffect(() => {
    if (convError && String(convError).includes("404")) {
      router.replace("/app/inbox");
    }
  }, [convError, router]);

  async function handleSend(body: string) {
    await sendMessage(conversationId, body);
    mutate(["conversation", conversationId]);
    mutate(["conversations-list", filter, debouncedSearch]);
  }

  return (
    <div className="inbox-root">
      <div className="inbox-list-col">
        <InboxFilters
          value={filter} onChange={setFilter}
          search={search} onSearchChange={setSearch}
        />
        {list && <InboxList items={list} selectedId={conversationId} />}
      </div>
      <div className="inbox-conv-col">
        {conv ? (
          <ConversationView conversation={conv} onSend={handleSend} />
        ) : (
          <div className="inbox-empty">Carregando…</div>
        )}
      </div>
      <div className="inbox-rail-col">
        {conv && <ConversationRail conversation={conv} />}
      </div>
    </div>
  );
}
