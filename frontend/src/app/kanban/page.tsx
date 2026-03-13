"use client";

import { KanbanBoard } from "@/components/kanban-board";
import { PipelineControls } from "@/components/pipeline-controls";

export default function KanbanPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Kanban</h2>
      <PipelineControls onJobDone={() => window.location.reload()} />
      <KanbanBoard />
    </div>
  );
}
