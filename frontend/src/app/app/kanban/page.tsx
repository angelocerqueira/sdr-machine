"use client";

import { KanbanBoard } from "@/components/kanban-board";
import { PipelineControls } from "@/components/pipeline-controls";

export default function KanbanPage() {
  return (
    <div className="space-y-6 p-5 md:p-6" style={{ maxWidth: "calc(100vw - 64px)" }}>
      <div>
        <h2 className="text-2xl font-bold tracking-tight font-[family-name:var(--font-heading)]">Kanban</h2>
        <p className="text-text-secondary text-sm mt-1">Gerencie leads pelo pipeline</p>
      </div>
      <PipelineControls onJobDone={() => window.location.reload()} />
      <KanbanBoard />
    </div>
  );
}
