import { redirect } from "next/navigation";

export default function KanbanRedirect() {
  redirect("/app/pipeline?view=kanban");
}
