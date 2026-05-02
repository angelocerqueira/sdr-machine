import type { Lead } from "./types";

const HEADERS = [
  "lead_id",
  "public_id",
  "nome",
  "telefone",
  "email",
  "cidade",
  "nicho",
  "score",
  "status",
  "atualizado_em",
  "wa_link",
];

function escapeCSV(value: unknown): string {
  if (value == null) return "";
  const str = String(value);
  if (str.includes(",") || str.includes('"') || str.includes("\n")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

function buildWaLink(telefone: string | null): string {
  if (!telefone) return "";
  const cleaned = telefone.replace(/\D/g, "");
  if (!cleaned) return "";
  const withCountry = cleaned.startsWith("55") ? cleaned : `55${cleaned}`;
  return `https://wa.me/${withCountry}`;
}

export function leadToCsvRow(lead: Lead): string {
  return [
    escapeCSV(lead.id),
    escapeCSV(lead.public_id),
    escapeCSV(lead.nome),
    escapeCSV(lead.telefone),
    escapeCSV(lead.email),
    escapeCSV(lead.cidade),
    escapeCSV(lead.nicho),
    escapeCSV(lead.opportunity_score),
    escapeCSV(lead.status),
    escapeCSV(lead.updated_at),
    escapeCSV(buildWaLink(lead.telefone)),
  ].join(",");
}

export function exportLeadsCSV(leads: Lead[], filename: string = "leads.csv") {
  // UTF-8 BOM so Excel pt-BR renders accents correctly
  const bom = "﻿";
  const csv =
    bom +
    [HEADERS.join(","), ...leads.map(leadToCsvRow)].join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  // Defer revoke to next tick so the click triggers the download first
  setTimeout(() => URL.revokeObjectURL(url), 100);
}
