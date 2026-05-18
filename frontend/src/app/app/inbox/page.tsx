"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import { listConversations, type ConversationFilter } from "@/lib/api-inbox";
import { InboxList } from "@/components/inbox/InboxList";
import { InboxFilters } from "@/components/inbox/InboxFilters";
import { InboxEmpty } from "@/components/inbox/InboxEmpty";
import { useInboxState } from "@/components/inbox/use-inbox-state";
import "@/components/inbox/inbox.css";

export default function InboxPage() {
  const [filter, setFilter] = useState<ConversationFilter>("all");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const { data, error } = useSWR(
    ["conversations-list", filter, debouncedSearch],
    () => listConversations({ filter, search: debouncedSearch }),
    { refreshInterval: 5000 },
  );

  const emptyState = useInboxState({ conversations: data });

  return (
    <div className="inbox-root">
      <div className="inbox-list-col">
        <InboxFilters
          value={filter} onChange={setFilter}
          search={search} onSearchChange={setSearch}
        />
        {error && <div style={{ padding: 16, color: "var(--terra)" }}>Erro: {String(error)}</div>}
        {data && <InboxList items={data} selectedId={null} />}
      </div>
      <div className="inbox-conv-col">
        <InboxEmpty state={emptyState} />
      </div>
      <div className="inbox-rail-col" />
    </div>
  );
}
