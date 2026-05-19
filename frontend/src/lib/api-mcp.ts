import type { McpTokenCreated, McpTokenSummary } from "./settings-types";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

async function authedFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getSessionToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { ...init, headers, credentials: "include" });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`${res.status}: ${txt}`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const listMcpTokens = () =>
  authedFetch<McpTokenSummary[]>("/api/workspace/mcp-tokens");

export const createMcpToken = (name: string) =>
  authedFetch<McpTokenCreated>("/api/workspace/mcp-tokens", {
    method: "POST",
    body: JSON.stringify({ name }),
  });

export const revokeMcpToken = (id: number) =>
  authedFetch<void>(`/api/workspace/mcp-tokens/${id}`, { method: "DELETE" });
