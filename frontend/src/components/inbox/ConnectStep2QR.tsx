"use client";

import { useCallback, useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import useSWR from "swr";
import {
  connectEvolution,
  getEvolutionStatus,
  type EvolutionConnectResponse,
} from "@/lib/api-settings";

interface Props {
  onConnected: () => void;  // dispara quando state="open"
}

function stateLabel(state: string): string {
  switch (state) {
    case "open": return "Conectado";
    case "connecting": return "Aguardando scan…";
    case "close": return "Desconectado";
    case "unreachable": return "Servidor inacessível";
    case "error": return "Erro";
    default: return state;
  }
}

function stateClass(state: string): string {
  if (state === "open") return "open";
  if (state === "connecting") return "connecting";
  if (state === "unreachable" || state === "error" || state === "close") return "err";
  return "";
}

export function ConnectStep2QR({ onConnected }: Props) {
  const [conn, setConn] = useState<EvolutionConnectResponse | null>(null);
  const [loadingQR, setLoadingQR] = useState(true);
  const [qrError, setQrError] = useState<string | null>(null);

  const refreshQR = useCallback(async () => {
    setLoadingQR(true);
    setQrError(null);
    try {
      const res = await connectEvolution();
      setConn(res);
      if (!res.ok) {
        setQrError(res.error || "Falhou ao gerar QR.");
      }
    } catch (e) {
      setQrError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingQR(false);
    }
  }, []);

  useEffect(() => {
    refreshQR();
  }, [refreshQR]);

  // Polling status a cada 3s — skip first fetch if we already have state from connect
  const { data: status } = useSWR("evolution-status", getEvolutionStatus, {
    refreshInterval: 3000,
    revalidateOnFocus: false,
    revalidateOnMount: !conn,
    fallbackData:
      conn?.ok && conn.state
        ? { state: conn.state, ok: conn.state === "open", latency_ms: 0, error: null }
        : undefined,
  });

  const connState = conn?.ok ? conn.state : "unknown";
  const currentState = status?.state ?? connState;

  useEffect(() => {
    if (currentState === "open") {
      const t = setTimeout(onConnected, 600);  // pausa pra user ver "Conectado"
      return () => clearTimeout(t);
    }
  }, [currentState, onConnected]);

  const qrSrc = conn?.ok ? conn.qr_base64 : null;
  const codeText = conn?.ok ? conn.code : null;
  const isImage = qrSrc?.startsWith("data:image/") ?? false;
  // Evolution v2 /instance/connect retorna apenas {pairingCode, code}.
  // Base64 só vem via webhook/websocket. Renderizamos QR client-side
  // a partir do `code` raw string (formato WhatsApp Web auth payload).

  return (
    <div>
      <div className="connect-qr-wrap">
        {loadingQR ? (
          <div className="connect-qr-placeholder">Gerando QR…</div>
        ) : qrError ? (
          <div className="connect-qr-placeholder" style={{ color: "var(--terra)" }}>{qrError}</div>
        ) : isImage && qrSrc ? (
          <div className="connect-qr-frame">
            { /* eslint-disable-next-line @next/next/no-img-element */ }
            <img className="connect-qr-img" src={qrSrc} alt="QR code Evolution" />
          </div>
        ) : codeText ? (
          <div className="connect-qr-frame">
            <QRCodeSVG
              value={codeText}
              size={240}
              level="M"
              marginSize={2}
            />
          </div>
        ) : (
          <div className="connect-qr-placeholder">QR indisponível</div>
        )}

        <span className={`connect-state-pill ${stateClass(currentState)}`}>
          <span className="dot" />
          {stateLabel(currentState)}
        </span>
      </div>

      <ol className="connect-qr-steps">
        <li className="connect-qr-step">
          <span className="connect-qr-step-num">01</span>
          <span>Abra o WhatsApp no celular</span>
        </li>
        <li className="connect-qr-step">
          <span className="connect-qr-step-num">02</span>
          <span>Menu (⋮) → <strong>Dispositivos conectados</strong></span>
        </li>
        <li className="connect-qr-step">
          <span className="connect-qr-step-num">03</span>
          <span>Toque em <strong>Conectar um dispositivo</strong></span>
        </li>
        <li className="connect-qr-step">
          <span className="connect-qr-step-num">04</span>
          <span>Aponte a câmera pro QR acima</span>
        </li>
      </ol>

      <div style={{ marginTop: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
          QR expira em ~60s.
        </span>
        <button className="connect-btn" onClick={refreshQR} disabled={loadingQR}>
          {loadingQR ? "Atualizando…" : "Atualizar QR"}
        </button>
      </div>
    </div>
  );
}
