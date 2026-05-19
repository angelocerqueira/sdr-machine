"use client";

import { useState, useEffect, useRef } from "react";
import useSWR, { mutate as globalMutate } from "swr";
import { listConversations, type ConversationFilter } from "@/lib/api-inbox";
import { getEvolutionStatus, logoutEvolution } from "@/lib/api-settings";
import { InboxList } from "@/components/inbox/InboxList";
import { InboxFilters } from "@/components/inbox/InboxFilters";
import { InboxEmpty } from "@/components/inbox/InboxEmpty";
import { ConnectEvolutionSheet } from "@/components/inbox/ConnectEvolutionSheet";
import { ShortcutsModal } from "@/components/inbox/ShortcutsModal";
import { useInboxState } from "@/components/inbox/use-inbox-state";
import { useInboxShortcuts } from "@/components/inbox/use-inbox-shortcuts";
import "@/components/inbox/inbox.css";

const RECONNECT_CONFIRM =
  "Desconectar vai parar de receber mensagens até você escanear o QR novamente. " +
  "Mensagens em rota podem falhar. Continuar?";

export default function InboxPage() {
  const [filter, setFilter] = useState<ConversationFilter>("all");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [reconnecting, setReconnecting] = useState(false);
  const [connectSheetOpen, setConnectSheetOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const searchInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const { data, error } = useSWR(
    ["conversations-list", filter, debouncedSearch],
    () => listConversations({ filter, search: debouncedSearch }),
    { refreshInterval: 5000 },
  );

  // Shares the SWR key with useInboxState — dedupes the fetch.
  const { data: status } = useSWR("evolution-status", getEvolutionStatus, {
    refreshInterval: 15000,
    revalidateOnFocus: true,
  });

  const emptyState = useInboxState({ conversations: data });
  const showList = !["not-configured", "disconnected"].includes(emptyState.kind);

  useInboxShortcuts({
    list: data,
    selectedId: null,
    setFilter,
    setSearch,
    onShowShortcuts: () => setShortcutsOpen(true),
    searchInputRef,
  });

  async function handleReconnect() {
    if (!window.confirm(RECONNECT_CONFIRM)) return;
    setReconnecting(true);
    try {
      await logoutEvolution();
      // Status vai pra "close" — força revalidate pra pill sumir antes do modal abrir
      await globalMutate("evolution-status");
      setConnectSheetOpen(true);
    } catch (e) {
      window.alert("Falha ao desconectar: " + String(e));
    } finally {
      setReconnecting(false);
    }
  }

  return (
    <div className="inbox-root">
      {showList && (
        <div className="inbox-list-col">
          <InboxFilters
            value={filter} onChange={setFilter}
            search={search} onSearchChange={setSearch}
            connectionState={status?.state}
            onReconnect={handleReconnect}
            reconnecting={reconnecting}
            inputRef={searchInputRef}
          />
          {error && <div style={{ padding: 16, color: "var(--terra)" }}>Erro: {String(error)}</div>}
          {data && <InboxList items={data} selectedId={null} />}
        </div>
      )}
      <div className="inbox-conv-col">
        <InboxEmpty state={emptyState} />
      </div>
      {showList && <div className="inbox-rail-col" />}

      <ConnectEvolutionSheet
        open={connectSheetOpen}
        initialStep={2}
        onClose={() => setConnectSheetOpen(false)}
        onConnected={() => {
          setConnectSheetOpen(false);
          globalMutate("evolution-status");
        }}
      />

      <ShortcutsModal open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </div>
  );
}
