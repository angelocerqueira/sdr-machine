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


# ---------------------------------------------------------------------------
# Tratamento formal inference (PR3.2)
# ---------------------------------------------------------------------------
# When a regulated nicho has exactly one identifiable sócio, we infer the
# appropriate honorific (Dr/Dra) for outreach messaging. Purely heuristic —
# no LLM, no DB. The inference is intentionally conservative: 0 or 2+ sócios
# fall back to None (a neutral "Oi" greeting). Manual overrides on the lead
# are preserved by the caller (see ``apply_enrichment_result``).

_REGULATED_NICHOS = {
    "advocacia",
    "medicina",
    "odontologia",
    "clinica_medica",
    "dentista",
    "fisioterapia",
    "psicologia",
    "veterinaria",
    "veterinária",
}

_COMMON_FEMALE_FIRST_NAMES = frozenset({
    "maria", "ana", "fernanda", "patricia", "patrícia", "juliana", "amanda",
    "camila", "cristina", "monica", "mônica", "carla", "andrea", "andréa",
    "renata", "marcela", "vanessa", "bruna", "raquel", "luciana", "claudia",
    "cláudia", "beatriz", "isabel", "isabela", "rosa", "rita", "sandra",
    "silvia", "sílvia", "tatiana", "viviane", "denise", "alice", "helena",
    "regina", "marta", "lucia", "lúcia", "sara", "leticia", "letícia",
    "natalia", "natália", "joana", "antonia", "antônia", "francisca",
    "teresa", "tereza", "sonia", "sônia", "miriam", "yara", "vera",
    "elaine", "michele", "michelle", "priscila", "rafaela", "carolina",
    "gabriela", "larissa", "manuela", "valeria", "valéria", "adriana",
})


def _normalize_nicho(*candidates: str | None) -> set[str]:
    return {(c or "").strip().lower() for c in candidates if c}


def _is_regulated_nicho(*nichos: str | None) -> bool:
    return bool(_normalize_nicho(*nichos) & _REGULATED_NICHOS)


def _extract_socio_names(socios) -> list[str]:
    """Return list of socio names from various shapes (dict, str, etc.). Skip empty."""
    out: list[str] = []
    for s in (socios or []):
        if isinstance(s, dict):
            name = (
                s.get("nome")
                or s.get("name")
                or s.get("razao_social")
                or s.get("descricao")
            )
        elif isinstance(s, str):
            name = s
        else:
            name = None
        if name and isinstance(name, str) and name.strip():
            out.append(name.strip())
    return out


def _is_female_first_name(name: str) -> bool:
    parts = (name or "").strip().lower().split()
    return bool(parts) and parts[0] in _COMMON_FEMALE_FIRST_NAMES


def infer_tratamento_formal(
    nicho: str | None,
    nicho_canonico: str | None,
    socios,
) -> str | None:
    """Pure inference function — easy to test in isolation.

    Returns "Dr"/"Dra" only when the nicho is regulated AND there is exactly
    one identifiable sócio. Otherwise returns None (fall back to neutral
    greeting in outreach).
    """
    if not _is_regulated_nicho(nicho, nicho_canonico):
        return None
    names = _extract_socio_names(socios)
    if len(names) != 1:
        return None
    return "Dra" if _is_female_first_name(names[0]) else "Dr"


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

        # Tratamento formal inference (PR3.2). Only set if non-None — the
        # consumer (apply_enrichment_result) preserves manual overrides.
        inferred = infer_tratamento_formal(
            getattr(lead, "nicho", None),
            getattr(lead, "nicho_canonico", None),
            socios,
        )
        if inferred:
            data["tratamento_formal"] = inferred

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
