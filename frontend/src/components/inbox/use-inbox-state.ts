"use client";

import useSWR from "swr";
import { getIntegration, getEvolutionStatus } from "@/lib/api-settings";
import type { ConversationListItem } from "@/lib/api-inbox";

export type InboxState =
  | { kind: "loading" }
  | { kind: "not-configured" }
  | { kind: "disconnected"; state: string }
  | { kind: "connected-empty" }
  | { kind: "connected-with-convs" };

interface Args {
  conversations: ConversationListItem[] | undefined;
}

export function useInboxState({ conversations }: Args): InboxState {
  const { data: integration } = useSWR(
    "integration-evolution",
    () => getIntegration("evolution").catch(() => null),
    { refreshInterval: 0, revalidateOnFocus: true },
  );

  const credsOk = Boolean(
    integration?.enabled &&
      integration?.config?.has_api_key &&
      integration?.config?.has_webhook_secret,
  );

  const { data: status } = useSWR(
    credsOk ? "evolution-status" : null,
    getEvolutionStatus,
    { refreshInterval: 15000, revalidateOnFocus: true },
  );

  if (integration === undefined) return { kind: "loading" };
  if (!credsOk) return { kind: "not-configured" };
  if (!status) return { kind: "loading" };
  if (status.state !== "open") return { kind: "disconnected", state: status.state };
  if (!conversations) return { kind: "loading" };
  if (conversations.length === 0) return { kind: "connected-empty" };
  return { kind: "connected-with-convs" };
}
