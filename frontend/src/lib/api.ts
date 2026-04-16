import type { LeadListResponse, Lead, Job, JobListResponse, DashboardStats, Settings, OutreachMessage, LandingPage, EnrichRequest } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let redirectingToLogin = false;

function forceLogout() {
  if (redirectingToLogin) return;
  redirectingToLogin = true;
  // Limpa cookies de sessão para que o middleware também redirecione
  document.cookie.split("; ").forEach((c) => {
    const name = c.split("=")[0];
    if (name.includes("better-auth")) {
      document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
    }
  });
  window.location.replace("/login");
}

function getSessionToken(): string | null {
  // Better Auth session_token cookie is HttpOnly — document.cookie can't read it.
  // The cookieCache option creates a non-HttpOnly session_data cookie we CAN read.
  const cookies = document.cookie.split("; ");
  for (const c of cookies) {
    if (c.startsWith("__Secure-better-auth.session_data=") || c.startsWith("better-auth.session_data=")) {
      try {
        const val = decodeURIComponent(c.split("=").slice(1).join("="));
        const data = JSON.parse(atob(val));
        return data?.session?.session?.token || null;
      } catch { /* ignore parse errors */ }
    }
  }
  // Fallback: try session_token in case httpOnly was disabled
  for (const c of cookies) {
    if (c.startsWith("__Secure-better-auth.session_token=") || c.startsWith("better-auth.session_token=")) {
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
    // Call Better Auth getSession to refresh the cookieCache (session_data cookie)
    const res = await fetch("/api/auth/get-session", { credentials: "include" });
    if (res.ok) {
      // session_data cookie should now be refreshed by Better Auth
      return getSessionToken() !== null;
    }
    return false;
  } catch {
    return false;
  } finally {
    refreshingSession = false;
  }
}

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  let token = getSessionToken();

  // If no token, try refreshing the session cache before giving up
  if (!token) {
    const refreshed = await refreshSessionCache();
    if (refreshed) {
      token = getSessionToken();
    }
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...options?.headers as Record<string, string>,
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  // On 401, try one session refresh before logging out
  if (res.status === 401 && token) {
    const refreshed = await refreshSessionCache();
    if (refreshed) {
      const retryToken = getSessionToken();
      if (retryToken) {
        headers["Authorization"] = `Bearer ${retryToken}`;
        const retry = await fetch(`${API}${path}`, {
          ...options,
          headers,
          credentials: "include",
        });
        if (retry.ok) return retry.json();
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
    const error = await res.text();
    throw new Error(`API error ${res.status}: ${error}`);
  }
  return res.json();
}

// Leads
export const getLeads = (params?: Record<string, string>) => {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return fetchAPI<LeadListResponse>(`/api/leads${qs}`);
};

export const getLeadFilters = () =>
  fetchAPI<{ nichos: string[]; cidades: string[] }>("/api/leads/filters");

export const getLeadCounts = (params?: Record<string, string>) => {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return fetchAPI<Record<string, number>>(`/api/leads/counts${qs}`);
};

export const getLead = (id: number) => fetchAPI<Lead>(`/api/leads/${id}`);

export const updateLead = (id: number, data: { status?: string }) =>
  fetchAPI<Lead>(`/api/leads/${id}`, { method: "PATCH", body: JSON.stringify(data) });

export const deleteLead = async (id: number) => {
  const token = getSessionToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API}/api/leads/${id}`, { method: "DELETE", headers });
  if (res.status === 401) { forceLogout(); throw new Error("Sessão expirada"); }
  return res;
};

export const getLeadLpUrl = (id: number) => `${API}/api/leads/${id}/lp`;

export const getLeadByPublicId = (publicId: string) =>
  fetchAPI<Lead>(`/api/leads/p/${publicId}`);

export const getLeadLpUrlByPublicId = (publicId: string) =>
  `${API}/api/leads/p/${publicId}/lp`;

export const getLeadMessages = (leadId: number) =>
  fetchAPI<OutreachMessage[]>(`/api/leads/${leadId}/messages`);

// Landing Pages
export const getLeadLandingPages = (leadId: number) =>
  fetchAPI<LandingPage[]>(`/api/leads/${leadId}/landing-pages`);

export const activateLandingPage = (leadId: number, lpId: number) =>
  fetchAPI<LandingPage>(`/api/leads/${leadId}/landing-pages/${lpId}/activate`, { method: "POST" });

// Dashboard
export const getDashboardStats = () => fetchAPI<DashboardStats>("/api/dashboard/stats");

// Jobs
export const getJobs = (params?: Record<string, string>) => {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return fetchAPI<JobListResponse>(`/api/jobs${qs}`);
};

export const getJob = (id: number) => fetchAPI<Job>(`/api/jobs/${id}`);

export const streamJob = (id: number, onEvent: (event: { type: string; message: string }) => void) => {
  const controller = new AbortController();

  (async () => {
    try {
      const token = getSessionToken();
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const res = await fetch(`${API}/api/jobs/${id}/stream`, {
        headers,
        signal: controller.signal,
      });
      if (res.status === 401) { forceLogout(); return; }
      if (!res.ok || !res.body) return;

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = JSON.parse(line.slice(6));
          onEvent(data);
          if (data.type === "done" || data.type === "error") {
            controller.abort();
            return;
          }
        }
      }
    } catch {
      // aborted or network error
    }
  })();

  return () => controller.abort();
};

// Pipeline
export const runScrape = (params: {
  nichos?: string[];
  cidades?: string[];
  max_results?: number;
  fontes?: string[];
}) =>
  fetchAPI<Job>("/api/pipeline/scrape", { method: "POST", body: JSON.stringify(params) });

export const runEnrich = (params: EnrichRequest) =>
  fetchAPI<Job>("/api/pipeline/enrich", { method: "POST", body: JSON.stringify(params) });

export const runGenerate = (params: { lead_ids?: number[]; max_count?: number }) =>
  fetchAPI<Job>("/api/pipeline/generate", { method: "POST", body: JSON.stringify(params) });

export const runOutreach = (params: { lead_ids?: number[] }) =>
  fetchAPI<Job>("/api/pipeline/outreach", { method: "POST", body: JSON.stringify(params) });

// Pipeline Status
export const getPipelineStatus = () =>
  fetchAPI<{ eligible_counts: Record<string, number>; running_jobs: string[] }>("/api/pipeline/status");

// Settings
export const getSettings = () => fetchAPI<Settings>("/api/settings");

export async function importCSV(file: File, nicho: string, cidade: string): Promise<Job> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("nicho", nicho);
  formData.append("cidade", cidade);

  const token = getSessionToken();
  const res = await fetch(`${API}/api/pipeline/csv-import`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    credentials: "include",
    body: formData,
  });

  if (res.status === 401) {
    forceLogout();
    throw new Error("Sessão expirada");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || `Erro ${res.status}`);
  }

  return res.json();
}
