"use client";

import { Icon } from "@/components/ui";
import type { LeadAppDetail } from "./lead-app-types";

export function LaTabInfo({ lead }: { lead: LeadAppDetail }) {
  const hasTech = lead.tech_stack.length > 0;
  const hasReviews = lead.top_reviews.length > 0;
  const hasAnything = hasTech || hasReviews || lead.website;

  if (!hasAnything) {
    return (
      <div className="state" style={{ margin: "32px auto" }}>
        <div className="state-icon">
          <Icon name="info" size={20} />
        </div>
        <div className="state-title">Sem informações adicionais</div>
        <div className="state-msg">
          Execute o enriquecimento para coletar tech stack, reviews e mais dados sobre este lead.
        </div>
      </div>
    );
  }

  return (
    <div className="la-info-grid">
      {/* Card 1: Stack detectado */}
      {hasTech && (
        <div className="la-info-card">
          <div className="la-info-card-head">Stack detectado</div>
          <div className="la-tech-list">
            {lead.tech_stack.map((t, i) => {
              const warn = /jquery 1|bootstrap 3|wordpress 5/i.test(t.name);
              return (
                <span key={i} className={`la-tech ${warn ? "warn" : ""}`}>
                  {t.name}
                  <span className="cat">{t.category}</span>
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Card 2: Top reviews */}
      {hasReviews && (
        <div className="la-info-card">
          <div className="la-info-card-head">Top reviews · Google Maps</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {lead.top_reviews.map((r, i) => (
              <div
                key={i}
                style={{
                  fontSize: 12,
                  color: "var(--text-body)",
                  lineHeight: 1.55,
                  paddingLeft: 12,
                  borderLeft: "2px solid var(--border)",
                }}
              >
                &ldquo;{r}&rdquo;
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
