import type { LeadListResponse, Lead, Job, JobListResponse, DashboardStats, Settings, OutreachMessage } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
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

export const getLead = (id: number) => fetchAPI<Lead>(`/api/leads/${id}`);

export const updateLead = (id: number, data: { status?: string }) =>
  fetchAPI<Lead>(`/api/leads/${id}`, { method: "PATCH", body: JSON.stringify(data) });

export const deleteLead = (id: number) =>
  fetch(`${API}/api/leads/${id}`, { method: "DELETE" });

export const getLeadLpUrl = (id: number) => `${API}/api/leads/${id}/lp`;

export const getLeadMessages = (leadId: number) =>
  fetchAPI<OutreachMessage[]>(`/api/leads/${leadId}/messages`);

// Dashboard
export const getDashboardStats = () => fetchAPI<DashboardStats>("/api/dashboard/stats");

// Jobs
export const getJobs = (params?: Record<string, string>) => {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return fetchAPI<JobListResponse>(`/api/jobs${qs}`);
};

export const getJob = (id: number) => fetchAPI<Job>(`/api/jobs/${id}`);

export const streamJob = (id: number, onEvent: (event: { type: string; message: string }) => void) => {
  const source = new EventSource(`${API}/api/jobs/${id}/stream`);
  source.onmessage = (e) => {
    const data = JSON.parse(e.data);
    onEvent(data);
    if (data.type === "done" || data.type === "error") {
      source.close();
    }
  };
  source.onerror = () => source.close();
  return () => source.close();
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

// Settings
export const getSettings = () => fetchAPI<Settings>("/api/settings");
