"use client";

import { useState } from "react";
import Link from "next/link";
import { mutate } from "swr";
import { ConnectEvolutionSheet } from "./ConnectEvolutionSheet";
import { WebhookUrlField } from "@/components/settings/webhook-url-field";
import type { InboxState } from "./use-inbox-state";
import "./inbox-empty.css";

interface Props {
  state: InboxState;
}

function WhatsappMark() {
  return (
    <svg width="56" height="56" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    </svg>
  );
}

function ClockMark() {
  return (
    <svg width="56" height="56" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <polyline points="12 7 12 12 15 14" />
    </svg>
  );
}

function MailMark() {
  return (
    <svg width="56" height="56" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true">
      <rect x="3" y="6" width="18" height="14" rx="2" />
      <polyline points="3 8 12 14 21 8" />
    </svg>
  );
}

export function InboxEmpty({ state }: Props) {
  const [sheetOpen, setSheetOpen] = useState(false);
  const [sheetStep, setSheetStep] = useState<1 | 2>(1);

  function openSheet(step: 1 | 2) {
    setSheetStep(step);
    setSheetOpen(true);
  }

  function onConnected() {
    setSheetOpen(false);
    mutate("integration-evolution");
    mutate("evolution-status");
  }

  if (state.kind === "loading") {
    return (
      <div className="inbox-empty-wrap">
        <div className="inbox-empty-skeleton" />
      </div>
    );
  }

  if (state.kind === "not-configured") {
    return (
      <>
        <div className="inbox-empty-wrap">
          <div className="inbox-empty-icon" aria-hidden="true"><WhatsappMark /></div>
          <h2 className="inbox-empty-title">Conecte seu WhatsApp</h2>
          <p className="inbox-empty-text">
            Outreach automático aparece aqui assim que conversas começarem a chegar.
          </p>

          <ol className="inbox-empty-steps">
            <li><span className="inbox-empty-step-num">01</span><span>Configure as credenciais da sua Evolution API</span></li>
            <li><span className="inbox-empty-step-num">02</span><span>Escaneie o QR code com o WhatsApp do operador</span></li>
            <li><span className="inbox-empty-step-num">03</span><span>Receba a primeira mensagem inbound</span></li>
          </ol>

          <div className="inbox-empty-actions">
            <button className="connect-btn primary" onClick={() => openSheet(1)}>
              Conectar agora →
            </button>
            <Link href="/app/settings/integracoes/evolution" className="inbox-empty-link">
              Configurar via Settings
            </Link>
          </div>
        </div>
        <ConnectEvolutionSheet
          open={sheetOpen}
          initialStep={sheetStep}
          onClose={() => setSheetOpen(false)}
          onConnected={onConnected}
        />
      </>
    );
  }

  if (state.kind === "disconnected") {
    return (
      <>
        <div className="inbox-empty-wrap">
          <div className="inbox-empty-icon" aria-hidden="true"><WhatsappMark /></div>
          <h2 className="inbox-empty-title">Escaneie pra ativar</h2>
          <p className="inbox-empty-text">
            Credenciais salvas, mas a instância Evolution não está conectada ao WhatsApp.
            {state.state && state.state !== "unknown" && (
              <> Estado atual: <code style={{ fontFamily: "var(--font-jetbrains-mono, monospace)", fontSize: 12, color: "var(--text-muted)" }}>{state.state}</code>.</>
            )}
          </p>

          <div className="inbox-empty-actions">
            <button className="connect-btn primary" onClick={() => openSheet(2)}>
              Abrir QR code
            </button>
            <button className="inbox-empty-link" onClick={() => openSheet(1)}>
              Revisar credenciais
            </button>
          </div>
        </div>
        <ConnectEvolutionSheet
          open={sheetOpen}
          initialStep={sheetStep}
          onClose={() => setSheetOpen(false)}
          onConnected={onConnected}
        />
      </>
    );
  }

  if (state.kind === "connected-empty") {
    return (
      <div className="inbox-empty-wrap">
        <div className="inbox-empty-icon" style={{ color: "var(--salvia, #88c08a)" }} aria-hidden="true">
          <ClockMark />
        </div>
        <h2 className="inbox-empty-title">Aguardando primeira mensagem</h2>
        <p className="inbox-empty-text">
          Dispare uma cadência ou peça pra um lead te chamar. Quando alguém responder no WhatsApp do operador, a conversa aparece aqui.
        </p>

        <div className="inbox-empty-webhook">
          <WebhookUrlField
            provider="evolution"
            label="URL do webhook"
            hint="Configurada no painel Evolution pra entregar mensagens recebidas."
          />
        </div>
      </div>
    );
  }

  // connected-with-convs — placeholder "selecione uma conversa"
  return (
    <div className="inbox-empty-wrap simple">
      <div className="inbox-empty-icon-sm" aria-hidden="true"><MailMark /></div>
      <p className="inbox-empty-text-sm">Selecione uma conversa pra ler.</p>
    </div>
  );
}
