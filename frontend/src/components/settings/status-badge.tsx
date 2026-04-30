import type { IntegrationSummary } from "@/lib/settings-types";

export function StatusBadge({ integration }: { integration: IntegrationSummary }) {
  const isConfigured = Object.entries(integration.config).some(
    ([k, v]) => k.startsWith("has_") && v === true,
  );
  if (!isConfigured) return <span className="settings-badge settings-badge-muted">Desconectado</span>;
  if (!integration.last_test_result) return <span className="settings-badge settings-badge-warn">Não testado</span>;
  if (integration.last_test_result.ok) return <span className="settings-badge settings-badge-ok">Conectado</span>;
  return <span className="settings-badge settings-badge-danger">Falha</span>;
}
