import type { LeadListResponse, Lead, Job, JobListResponse, DashboardStats, Settings, OutreachMessage, LandingPage } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getSessionToken();
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
  });
  if (res.status === 401) {
    window.location.href = "/login";
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

export const deleteLead = (id: number) => {
  const token = getSessionToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return fetch(`${API}/api/leads/${id}`, { method: "DELETE", headers });
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
export const runScrape = (params: { nichos?: string[]; cidades?: string[]; max_results?: number }) =>
  fetchAPI<Job>("/api/pipeline/scrape", { method: "POST", body: JSON.stringify(params) });

export const runEnrich = (params: { lead_ids?: number[] }) =>
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
