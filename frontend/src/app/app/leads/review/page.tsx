import { ReviewTable } from "./review-table";

export default function ReviewPage() {
  return (
    /* span all columns of la-shell grid so the page isn't trapped in the 320px master column */
    <div style={{ gridColumn: "1 / -1", overflowY: "auto", height: "100%" }}>
      <div className="p-5 md:p-6 max-w-7xl">
        <div className="mb-8">
          <h2 className="text-2xl font-bold tracking-tight font-[family-name:var(--font-heading)]">
            Revisão de nichos
          </h2>
          <p className="text-text-secondary text-sm mt-1">
            Leads com classificação incerta ou que caíram em &quot;outros&quot; — revise manualmente.
          </p>
        </div>
        <ReviewTable />
      </div>
    </div>
  );
}
