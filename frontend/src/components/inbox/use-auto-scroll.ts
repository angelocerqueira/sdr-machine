import { useEffect, useRef, useState, useCallback } from "react";

interface AutoScrollReturn {
  scrollRef: React.RefObject<HTMLDivElement | null>;
  isAtBottom: boolean;
  newMessagesCount: number;
  scrollToBottom: (smooth?: boolean) => void;
}

const BOTTOM_THRESHOLD = 80; // px — distância do bottom pra considerar "at bottom"

export function useAutoScroll(messagesLength: number): AutoScrollReturn {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [newMessagesCount, setNewMessagesCount] = useState(0);
  const lastSeenLengthRef = useRef(messagesLength);

  const scrollToBottom = useCallback((smooth = true) => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({
      top: el.scrollHeight,
      behavior: smooth ? "smooth" : "auto",
    });
  }, []);

  // Detecta se user está perto do bottom
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;

    function onScroll() {
      if (!el) return;
      const nearBottom =
        el.scrollHeight - el.scrollTop - el.clientHeight < BOTTOM_THRESHOLD;
      setIsAtBottom(nearBottom);
      if (nearBottom) setNewMessagesCount(0);
    }

    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, []);

  // Reage a mudança em messagesLength
  useEffect(() => {
    const diff = messagesLength - lastSeenLengthRef.current;
    if (diff <= 0) {
      lastSeenLengthRef.current = messagesLength;
      return;
    }

    if (isAtBottom) {
      scrollToBottom(true);
      setNewMessagesCount(0);
    } else {
      setNewMessagesCount((c) => c + diff);
    }
    lastSeenLengthRef.current = messagesLength;
  }, [messagesLength, isAtBottom, scrollToBottom]);

  // Initial scroll on mount (sem smooth)
  useEffect(() => {
    scrollToBottom(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { scrollRef, isAtBottom, newMessagesCount, scrollToBottom };
}
