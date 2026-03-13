"use client";

import { useEffect, useState } from "react";
import { getJobs } from "@/lib/api";
import type { Job } from "@/lib/types";

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);

  useEffect(() => {
    getJobs().then((data) => setJobs(data.items));
  }, []);

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      pending: "bg-zinc-700 text-zinc-300",
      running: "bg-blue-900 text-blue-300",
      done: "bg-green-900 text-green-300",
      failed: "bg-red-900 text-red-300",
    };
    return colors[status] || colors.pending;
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Jobs</h2>
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-zinc-800 text-zinc-400">
            <tr>
              <th className="text-left p-3">ID</th>
              <th className="text-left p-3">Tipo</th>
              <th className="text-left p-3">Status</th>
              <th className="text-left p-3">Resultado</th>
              <th className="text-left p-3">Data</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id} className="border-t border-zinc-800">
                <td className="p-3 font-mono text-zinc-400">#{job.id}</td>
                <td className="p-3">{job.type}</td>
                <td className="p-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${statusBadge(job.status)}`}>
                    {job.status}
                  </span>
                </td>
                <td className="p-3 text-zinc-400">
                  {job.result_summary?.total
                    ? `${job.result_summary.success}/${job.result_summary.total} ok`
                    : job.error_message || "—"}
                </td>
                <td className="p-3 text-zinc-500">
                  {new Date(job.created_at).toLocaleString("pt-BR")}
                </td>
              </tr>
            ))}
            {jobs.length === 0 && (
              <tr>
                <td colSpan={5} className="p-6 text-center text-zinc-500">
                  Nenhum job executado ainda
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
