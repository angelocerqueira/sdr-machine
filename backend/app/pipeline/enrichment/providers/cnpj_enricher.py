"""CNPJ Enricher — consults BrasilAPI (free) for CNPJ data."""
from __future__ import annotations

import re
import logging
from datetime import datetime
import requests

from app.pipeline.enrichment.base_provider import (
    BaseProvider,
    EnrichmentContext,
    ProviderResult,
)

logger = logging.getLogger(__name__)

BRASILAPI_CNPJ_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"


def _clean_cnpj(cnpj: str) -> str:
    return re.sub(r"\D", "", cnpj or "")


class CnpjProvider(BaseProvider):
    name = "cnpj_enricher"
    display_name = "CNPJ Enricher (BrasilAPI)"
    required_fields = ["cnpj"]
    cost = "free"

    def can_run(self, lead, context: EnrichmentContext | None = None) -> bool:
        return bool(getattr(lead, "cnpj", None))

    def run(self, lead, context: EnrichmentContext) -> ProviderResult:
        cnpj_raw = getattr(lead, "cnpj", None)
        if not cnpj_raw:
            return ProviderResult(
                success=False, data={}, errors=["no cnpj"], source=self.name
            )

        cnpj = _clean_cnpj(cnpj_raw)
        if len(cnpj) != 14:
            return ProviderResult(
                success=False, data={}, errors=["invalid cnpj length"], source=self.name
            )

        try:
            resp = requests.get(
                BRASILAPI_CNPJ_URL.format(cnpj=cnpj), timeout=15
            )
        except Exception as exc:
            return ProviderResult(
                success=False,
                data={},
                errors=[f"http error: {str(exc)[:100]}"],
                source=self.name,
            )

        if resp.status_code != 200:
            return ProviderResult(
                success=False,
                data={},
                errors=[f"http {resp.status_code}"],
                source=self.name,
            )

        try:
            body = resp.json()
        except Exception as exc:
            return ProviderResult(
                success=False,
                data={},
                errors=[f"json: {str(exc)[:80]}"],
                source=self.name,
            )

        data: dict = {}
        if body.get("razao_social"):
            data["razao_social"] = body["razao_social"]
        if body.get("porte"):
            data["porte"] = body["porte"]
        if body.get("cnae_fiscal_descricao"):
            data["cnae"] = body["cnae_fiscal_descricao"]
        if body.get("data_inicio_atividade"):
            try:
                data["data_fundacao"] = datetime.strptime(
                    body["data_inicio_atividade"], "%Y-%m-%d"
                ).date().isoformat()
            except ValueError:
                pass

        qsa = body.get("qsa") or []
        socios = []
        for partner in qsa:
            nome = partner.get("nome_socio") or partner.get("nome") or ""
            if nome:
                socios.append({"nome": nome})
        if socios:
            data["socios"] = socios

        website = body.get("website") or ""
        if website and not getattr(lead, "website", None):
            context.discovered_website = website
            data["website"] = website

        return ProviderResult(
            success=True,
            data=data,
            errors=[],
            source=self.name,
        )
