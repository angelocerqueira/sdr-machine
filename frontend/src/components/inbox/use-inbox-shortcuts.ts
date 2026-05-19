import { useEffect } from "react";
import { useRouter } from "next/navigation";
import type { ConversationFilter, ConversationListItem } from "@/lib/api-inbox";

interface Args {
  list: ConversationListItem[] | undefined;
  selectedId: number | null;
  setFilter: (f: ConversationFilter) => void;
  setSearch: (s: string) => void;
  onShowShortcuts: () => void;
  searchInputRef?: React.RefObject<HTMLInputElement | null>;
}

const FILTER_KEYS: Record<string, ConversationFilter> = {
  "1": "all",
  "2": "unread",
  "3": "responded",
  "4": "won",
};

function isEditableTarget(e: KeyboardEvent): boolean {
  const t = e.target as HTMLElement;
  if (!t) return false;
  return (
    t.tagName === "INPUT" ||
    t.tagName === "TEXTAREA" ||
    t.isContentEditable
  );
}

export function useInboxShortcuts({
  list,
  selectedId,
  setFilter,
  setSearch,
  onShowShortcuts,
  searchInputRef,
}: Args) {
  const router = useRouter();

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const cmdOrCtrl = e.metaKey || e.ctrlKey;

      // Cmd+K → focus search (mesmo em textarea)
      if (cmdOrCtrl && e.key.toLowerCase() === "k") {
        e.preventDefault();
        searchInputRef?.current?.focus();
        return;
      }

      // Em campo editável: ignorar atalhos que não sejam Cmd+K
      if (isEditableTarget(e)) return;

      // ? → cheat sheet
      if (e.key === "?" && !cmdOrCtrl) {
        e.preventDefault();
        onShowShortcuts();
        return;
      }

      // Esc → volta pra /app/inbox
      if (e.key === "Escape") {
        if (selectedId !== null) router.push("/app/inbox");
        return;
      }

      // 1-4 → filtros
      if (FILTER_KEYS[e.key] !== undefined && !cmdOrCtrl) {
        e.preventDefault();
        setFilter(FILTER_KEYS[e.key]);
        return;
      }

      // J/K (ou ArrowDown/ArrowUp): navegar lista
      if ((e.key === "j" || e.key === "ArrowDown") && !cmdOrCtrl) {
        e.preventDefault();
        navigate(list, selectedId, 1, router);
        return;
      }
      if ((e.key === "k" || e.key === "ArrowUp") && !cmdOrCtrl) {
        e.preventDefault();
        navigate(list, selectedId, -1, router);
        return;
      }
    }

    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [list, selectedId, setFilter, setSearch, onShowShortcuts, router, searchInputRef]);
}

function navigate(
  list: ConversationListItem[] | undefined,
  currentId: number | null,
  delta: number,
  router: ReturnType<typeof useRouter>,
) {
  if (!list || list.length === 0) return;
  const idx =
    currentId === null
      ? delta > 0
        ? -1
        : list.length
      : list.findIndex((c) => c.id === currentId);
  const next = idx + delta;
  if (next < 0 || next >= list.length) return;
  router.push(`/app/inbox/${list[next].id}`);
}
