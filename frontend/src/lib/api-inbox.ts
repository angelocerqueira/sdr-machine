export type ConversationFilter = "all" | "unread" | "responded" | "won";

export interface Message {
  id: number;
  conversation_id: number;
  direction: "in" | "out";
  provider_message_id: string | null;
  body: string | null;
  media_url: string | null;
  status: string;
  sent_at: string | null;
  delivered_at: string | null;
  read_at: string | null;
  received_at: string | null;
  error: string | null;
  created_at: string;
}

export interface ConversationListItem {
  id: number;
  lead_id: number;
  lead_nome: string | null;
  lead_telefone: string | null;
  lead_status: string | null;
  provider: string;
  phone: string;
  last_message_at: string | null;
  last_message_preview: string | null;
  unread_count: number;
  status: string;
}

export interface ConversationDetail {
  id: number;
  workspace_id: number;
  lead_id: number;
  provider: string;
  provider_chat_id: string;
  phone: string;
  last_message_at: string | null;
  unread_count: number;
  status: string;
  created_at: string;
  messages: Message[];
}

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let redirectingToLogin = false;

function forceLogout() {
  if (redirectingToLogin) return;
  redirectingToLogin = true;
  document.cookie.split("; ").forEach((c) => {
    const name = c.split("=")[0];
    if (name.includes("better-auth")) {
      document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
    }
  });
  window.location.replace("/login");
}

function getSessionToken(): string | null {
  const cookies = document.cookie.split("; ");
  for (const c of cookies) {
    if (
      c.startsWith("__Secure-better-auth.session_data=") ||
      c.startsWith("better-auth.session_data=")
    ) {
      try {
        const val = decodeURIComponent(c.split("=").slice(1).join("="));
        const data = JSON.parse(atob(val));
        return data?.session?.session?.token || null;
      } catch {
        /* ignore */
      }
    }
  }
  // Fallback: session_token in case httpOnly was disabled
  for (const c of cookies) {
    if (
      c.startsWith("__Secure-better-auth.session_token=") ||
      c.startsWith("better-auth.session_token=")
    ) {
      const val = decodeURIComponent(c.split("=").slice(1).join("="));
      return val.split(".")[0];
    }
  }
  return null;
}

let refreshingSession = false;

async function refreshSessionCache(): Promise<boolean> {
  if (refreshingSession) return false;
  refreshingSession = true;
  try {
    const res = await fetch("/api/auth/get-session", { credentials: "include" });
    if (res.ok) return getSessionToken() !== null;
    return false;
  } catch {
    return false;
  } finally {
    refreshingSession = false;
  }
}

async function fetchInbox<T>(path: string, init: RequestInit = {}): Promise<T> {
  let token = getSessionToken();

  if (!token) {
    const refreshed = await refreshSessionCache();
    if (refreshed) token = getSessionToken();
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API}${path}`, { ...init, headers, credentials: "include" });

  // On 401, try one session refresh before logging out
  if (res.status === 401 && token) {
    const refreshed = await refreshSessionCache();
    if (refreshed) {
      const retryToken = getSessionToken();
      if (retryToken) {
        headers["Authorization"] = `Bearer ${retryToken}`;
        const retry = await fetch(`${API}${path}`, { ...init, headers, credentials: "include" });
        if (retry.ok) {
          return retry.status === 204 ? (undefined as T) : retry.json();
        }
      }
    }
    forceLogout();
    throw new Error("Sessão expirada");
  }

  if (res.status === 401) {
    forceLogout();
    throw new Error("Sessão expirada");
  }

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`${res.status}: ${txt}`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const listConversations = (params: { filter?: ConversationFilter; search?: string } = {}) => {
  const qs = new URLSearchParams();
  if (params.filter && params.filter !== "all") qs.set("filter", params.filter);
  if (params.search) qs.set("search", params.search);
  const tail = qs.toString() ? `?${qs.toString()}` : "";
  return fetchInbox<ConversationListItem[]>(`/api/conversations${tail}`);
};

export const getConversation = (id: number) =>
  fetchInbox<ConversationDetail>(`/api/conversations/${id}`);

export const sendMessage = (id: number, body: string) =>
  fetchInbox<Message>(`/api/conversations/${id}/messages`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });

export const markRead = (id: number) =>
  fetchInbox<ConversationListItem>(`/api/conversations/${id}/read`, {
    method: "PATCH",
  });
