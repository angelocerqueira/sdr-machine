"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  bulkDeleteLeads,
  bulkUpdateLeads,
  getJob,
  getPipelineStatus,
  previewPipeline,
  runEnrich,
  runGenerate,
  runOutreach,
} from "@/lib/api";
import { KANBAN_COLUMNS } from "@/lib/types";
import type { Job, PipelineAction, PipelinePreviewResponse } from "@/lib/types";
import type { useBulkSelection } from "./use-bulk-selection";
import { BulkConfirmModal } from "./bulk-confirm-modal";
import { BulkResultModal } from "./bulk-result-modal";
import { useToast } from "@/components/ui/toast";

// NOTE: PR 3/5 intentionally omits the "Editar ▾" dropdown and "Exportar CSV"
// from the action bar — those will land in PR 4/5 with their own confirm flows.

interface Props {
  sel: ReturnType<typeof useBulkSelection>;
  /** Called after a successful bulk action so caller can refetch data. */
  onChanged?: () => void;
}

type DialogState =
  | { kind: "none" }
  | {
      kind: "preview";
      action: PipelineAction;
      preview: PipelinePreviewResponse | null;
      pendingIds: number[];
    }
  | { kind: "move"; status: string; pendingIds: number[] }
  | { kind: "delete"; pendingIds: number[] };

const ACTION_LABEL: Record<PipelineAction, string> = {
  enrich: "Re-enriquecer",
  generate: "Gerar LP",
  outreach: "Gerar mensagens",
  classify: "Classificar",
};

export function BulkActionBar({ sel, onChanged }: Props) {
  const { toast } = useToast();
  const [dialog, setDialog] = useState<DialogState>({ kind: "none" });
  const [busy, setBusy] = useState(false);
  const [runningJobs, setRunningJobs] = useState<string[]>([]);
  const [moveMenuOpen, setMoveMenuOpen] = useState(false);
  const moveMenuRef = useRef<HTMLDivElement | null>(null);

  // Track the last bulk-dispatched job so we can surface a BulkResultModal
  // when it completes. We poll getJob(id) directly so fast jobs that finish
  // before the next global useActiveJobs tick are still detected. If a second
  // action is dispatched before the first completes, pendingJobId is replaced
  // (first modal won't show — acceptable).
  const [pendingJobId, setPendingJobId] = useState<number | null>(null);
  const [resultJob, setResultJob] = useState<Job | null>(null);

  useEffect(() => {
    if (pendingJobId == null) return;
    let cancelled = false;
    const TERMINAL = new Set(["done", "done_with_errors", "failed"]);

    const tick = async () => {
      try {
        const job = await getJob(pendingJobId);
        if (cancelled) return;
        if (TERMINAL.has(job.status)) {
          setResultJob(job);
          setPendingJobId(null);
        }
      } catch {
        // ignore — next tick will retry
      }
    };
    // Fast first poll so ms-scale jobs show their result modal immediately.
    tick();
    const id = setInterval(tick, 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [pendingJobId]);

  // Poll pipeline status to disable buttons when a same-type job is already running
  useEffect(() => {
    if (sel.size === 0) {
      setRunningJobs([]);
      return;
    }
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const poll = async () => {
      try {
        const status = await getPipelineStatus();
        if (!cancelled) setRunningJobs(status.running_jobs ?? []);
      } catch {
        // ignore
      }
      if (!cancelled) timer = setTimeout(poll, 5000);
    };
    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [sel.size]);

  // Close move menu on outside click
  useEffect(() => {
    if (!moveMenuOpen) return;
    function onDocClick(e: MouseEvent) {
      if (
        moveMenuRef.current &&
        !moveMenuRef.current.contains(e.target as Node)
      ) {
        setMoveMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [moveMenuOpen]);

  const isJobRunning = (action: PipelineAction) => runningJobs.includes(action);

  const dispatchAction = useCallback(
    async (action: PipelineAction) => {
      if (busy) return;
      setBusy(true);
      try {
        const ids = await sel.materializeIds();
        const preview = await previewPipeline({ action, lead_ids: ids });
        setDialog({ kind: "preview", action, preview, pendingIds: ids });
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Erro desconhecido";
        if (msg === "BULK_LIMIT_EXCEEDED") {
          toast(
            "Reduza o filtro pra ≤5000 leads ou aguarde endpoint by_filter.",
            { variant: "warning" },
          );
        } else {
          toast(`Erro: ${msg}`, { variant: "error" });
        }
      } finally {
        setBusy(false);
      }
    },
    [busy, sel, toast],
  );

  const handleConfirmAction = useCallback(
    async (opts?: { force?: boolean }) => {
      if (dialog.kind !== "preview") return;
      setBusy(true);
      try {
        const { action, pendingIds } = dialog;
        let job: Job | null = null;
        if (action === "enrich") {
          job = await runEnrich({
            lead_ids: pendingIds,
            force_providers: opts?.force
              ? ["website_crawler", "schema_extractor", "tech_stack"]
              : [],
          });
        } else if (action === "generate") {
          job = await runGenerate({ lead_ids: pendingIds });
        } else if (action === "outreach") {
          job = await runOutreach({ lead_ids: pendingIds });
        }
        if (job?.id != null) setPendingJobId(job.id);
        onChanged?.();
        toast("Job iniciado.", { variant: "success" });
        sel.clear();
        setDialog({ kind: "none" });
      } catch (err) {
        toast(
          `Erro: ${err instanceof Error ? err.message : "Erro desconhecido"}`,
          { variant: "error" },
        );
      } finally {
        setBusy(false);
      }
    },
    [dialog, sel, onChanged, toast],
  );

  const handleMove = useCallback(
    async (status: string) => {
      setMoveMenuOpen(false);
      try {
        const ids = await sel.materializeIds();
        setDialog({ kind: "move", status, pendingIds: ids });
      } catch (err) {
        toast(err instanceof Error ? err.message : "Erro", { variant: "error" });
      }
    },
    [sel, toast],
  );

  const handleConfirmMove = useCallback(async () => {
    if (dialog.kind !== "move") return;
    setBusy(true);
    try {
      await bulkUpdateLeads(dialog.pendingIds, { status: dialog.status });
      sel.clear();
      setDialog({ kind: "none" });
      onChanged?.();
    } catch (err) {
      toast(`Erro: ${err instanceof Error ? err.message : "Erro"}`, {
        variant: "error",
      });
    } finally {
      setBusy(false);
    }
  }, [dialog, sel, onChanged, toast]);

  const handleDelete = useCallback(async () => {
    try {
      const ids = await sel.materializeIds();
      setDialog({ kind: "delete", pendingIds: ids });
    } catch (err) {
      toast(err instanceof Error ? err.message : "Erro", { variant: "error" });
    }
  }, [sel, toast]);

  const handleConfirmDelete = useCallback(async () => {
    if (dialog.kind !== "delete") return;
    setBusy(true);
    try {
      await bulkDeleteLeads(dialog.pendingIds);
      sel.clear();
      setDialog({ kind: "none" });
      onChanged?.();
    } catch (err) {
      toast(`Erro: ${err instanceof Error ? err.message : "Erro"}`, {
        variant: "error",
      });
    } finally {
      setBusy(false);
    }
  }, [dialog, sel, onChanged, toast]);

  if (sel.size === 0) return null;

  const enrichDisabled = isJobRunning("enrich");
  const generateDisabled = isJobRunning("generate");
  const outreachDisabled = isJobRunning("outreach");

  const previewTitle =
    dialog.kind === "preview"
      ? `${ACTION_LABEL[dialog.action]} ${dialog.pendingIds.length} leads?`
      : "";
  const previewConfirmLabel =
    dialog.kind === "preview" ? ACTION_LABEL[dialog.action] : "";

  const moveTitle =
    dialog.kind === "move"
      ? `Mover ${dialog.pendingIds.length} leads para ${
          KANBAN_COLUMNS.find((c) => c.id === dialog.status)?.label ??
          dialog.status
        }?`
      : "";

  const deleteTitle =
    dialog.kind === "delete"
      ? `Excluir ${dialog.pendingIds.length} leads?`
      : "";
  const deleteCount = dialog.kind === "delete" ? dialog.pendingIds.length : 0;

  return (
    <>
      <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-border bg-surface shadow-2xl md:left-[64px]">
        <div className="flex flex-wrap items-center gap-2 px-4 py-3">
          <span className="t-eyebrow font-mono tabular-nums text-text">
            {sel.size} selecionado{sel.size === 1 ? "" : "s"}
          </span>
          <div className="ml-2 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={enrichDisabled || busy}
              onClick={() => dispatchAction("enrich")}
              className="rounded-md bg-accent-soft px-3 py-1.5 text-[13px] text-accent hover:opacity-80 disabled:opacity-50 transition-default cursor-pointer"
              title={
                enrichDisabled ? "Já existe um job de enrich em andamento" : ""
              }
            >
              {ACTION_LABEL.enrich}
            </button>
            <button
              type="button"
              disabled={generateDisabled || busy}
              onClick={() => dispatchAction("generate")}
              className="rounded-md bg-accent-soft px-3 py-1.5 text-[13px] text-accent hover:opacity-80 disabled:opacity-50 transition-default cursor-pointer"
              title={
                generateDisabled
                  ? "Já existe um job de generate em andamento"
                  : ""
              }
            >
              {ACTION_LABEL.generate}
            </button>
            <button
              type="button"
              disabled={outreachDisabled || busy}
              onClick={() => dispatchAction("outreach")}
              className="rounded-md bg-accent-soft px-3 py-1.5 text-[13px] text-accent hover:opacity-80 disabled:opacity-50 transition-default cursor-pointer"
              title={
                outreachDisabled
                  ? "Já existe um job de outreach em andamento"
                  : ""
              }
            >
              {ACTION_LABEL.outreach}
            </button>
            <div className="relative" ref={moveMenuRef}>
              <button
                type="button"
                disabled={busy}
                onClick={() => setMoveMenuOpen((v) => !v)}
                className="rounded-md border border-border bg-surface-raised px-3 py-1.5 text-[13px] text-text-secondary hover:border-border-strong hover:text-text disabled:opacity-50 transition-default cursor-pointer"
              >
                Mover para ▾
              </button>
              {moveMenuOpen && (
                <div className="absolute bottom-full mb-2 right-0 w-48 rounded-md border border-border bg-surface shadow-lg overflow-hidden">
                  {KANBAN_COLUMNS.map((col) => (
                    <button
                      key={col.id}
                      type="button"
                      onClick={() => handleMove(col.id)}
                      className="block w-full px-3 py-2 text-left text-[13px] text-text-secondary hover:bg-surface-raised hover:text-text transition-default cursor-pointer"
                    >
                      {col.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button
              type="button"
              disabled={busy}
              onClick={handleDelete}
              className="rounded-md border border-danger/30 bg-danger-soft px-3 py-1.5 text-[13px] text-danger hover:opacity-80 disabled:opacity-50 transition-default cursor-pointer"
            >
              Excluir
            </button>
            <button
              type="button"
              onClick={() => sel.clear()}
              className="rounded-md px-3 py-1.5 text-[13px] text-text-muted hover:text-text transition-default cursor-pointer"
            >
              ⨯ Limpar
            </button>
          </div>
        </div>
      </div>

      {dialog.kind === "preview" && (
        <BulkConfirmModal
          open
          onClose={() => setDialog({ kind: "none" })}
          onConfirm={handleConfirmAction}
          variant="soft"
          title={previewTitle}
          confirmLabel={previewConfirmLabel}
          preview={dialog.preview}
          showForceToggle={dialog.action === "enrich"}
          busy={busy}
        />
      )}

      {dialog.kind === "move" && (
        <BulkConfirmModal
          open
          onClose={() => setDialog({ kind: "none" })}
          onConfirm={handleConfirmMove}
          variant="soft"
          title={moveTitle}
          confirmLabel="Mover"
          busy={busy}
        />
      )}

      {dialog.kind === "delete" && (
        <BulkConfirmModal
          open
          onClose={() => setDialog({ kind: "none" })}
          onConfirm={handleConfirmDelete}
          variant="hard"
          title={deleteTitle}
          confirmLabel="Excluir"
          hardConfirmKeyword="EXCLUIR"
          description={
            <>
              <p>Vai apagar permanentemente:</p>
              <ul className="ml-4 list-disc text-text-muted">
                <li>{deleteCount} leads</li>
                <li>mensagens e LPs associadas (cascade)</li>
              </ul>
            </>
          }
          busy={busy}
        />
      )}

      <BulkResultModal job={resultJob} onClose={() => setResultJob(null)} />
    </>
  );
}
