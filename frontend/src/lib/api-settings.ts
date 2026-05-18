import type {
  WorkspaceProfile, WorkspaceTargeting,
  IntegrationSummary, ProviderId, TestResult,
} from "./settings-types";

export type { TestResult, IntegrationSummary, ProviderId } from "./settings-types";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function authedFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  // Reuse session token discovery from api.ts pattern
  const cookies = document.cookie.split("; ");
  let token: string | null = null;
  for (const c of cookies) {
    if (c.startsWith("__Secure-better-auth.session_data=") || c.startsWith("better-auth.session_data=")) {
      try {
        const val = decodeURIComponent(c.split("=").slice(1).join("="));
        const data = JSON.parse(atob(val));
        token = data?.session?.session?.token || null;
      } catch {}
    }
  }
  const res = await fetch(`${API}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers || {}),
    },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const getWorkspaceProfile  = () => authedFetch<WorkspaceProfile>("/api/workspace/profile");
export const updateWorkspaceProfile = (data: Partial<WorkspaceProfile>) =>
  authedFetch<WorkspaceProfile>("/api/workspace/profile", { method: "PUT", body: JSON.stringify(data) });

export const getWorkspaceTargeting = () => authedFetch<WorkspaceTargeting>("/api/workspace/targeting");
export const updateWorkspaceTargeting = (data: Partial<WorkspaceTargeting>) =>
  authedFetch<WorkspaceTargeting>("/api/workspace/targeting", { method: "PUT", body: JSON.stringify(data) });

export const listIntegrations  = () => authedFetch<IntegrationSummary[]>("/api/workspace/integrations");
export const getIntegration    = (provider: ProviderId) => authedFetch<IntegrationSummary>(`/api/workspace/integrations/${provider}`);
export const updateIntegration = (provider: ProviderId, config: Record<string, unknown>) =>
  authedFetch<IntegrationSummary>(`/api/workspace/integrations/${provider}`, {
    method: "PUT", body: JSON.stringify({ config }),
  });
export const deleteIntegration = (provider: ProviderId) =>
  authedFetch<void>(`/api/workspace/integrations/${provider}`, { method: "DELETE" });
export const testIntegration   = (provider: ProviderId) =>
  authedFetch<TestResult>(`/api/workspace/integrations/${provider}/test`, { method: "POST" });

export const getProviderWebhookUrl = (provider: ProviderId) =>
  authedFetch<{ url: string }>(`/api/workspace/integrations/${provider}/webhook-url`);

// Evolution-specific QR flow
export type EvolutionState =
  | "open"
  | "connecting"
  | "close"
  | "unreachable"
  | "error"
  | "unknown";

export type EvolutionConnectResponse =
  | {
      ok: true;
      qr_base64: string | null;
      pairing_code: string | null;
      code: string | null;
      state: string;
      latency_ms: number;
    }
  | {
      ok: false;
      error: string;
      status_code?: number;
      latency_ms: number;
    };

export interface EvolutionStatusResponse {
  state: string;  // "open" | "connecting" | "close" | "unreachable" | "error" | "unknown"
  ok: boolean;
  latency_ms: number;
  error: string | null;
}

export const connectEvolution = () =>
  authedFetch<EvolutionConnectResponse>("/api/workspace/integrations/evolution/connect", { method: "POST" });

export const getEvolutionStatus = () =>
  authedFetch<EvolutionStatusResponse>("/api/workspace/integrations/evolution/status");
