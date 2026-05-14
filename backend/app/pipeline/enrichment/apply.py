"""Apply an orchestrator result dict to a Lead ORM instance.

Extracted from `routers/pipeline.py` so the background job and one-off
scripts share the exact same mapping rules.
"""
from __future__ import annotations

from datetime import datetime


def apply_enrichment_result(lead, result: dict) -> None:
    """Mutate *lead* in place with the fields contained in *result*.

    Callers are still responsible for committing the session and updating
    ``lead.status`` to the appropriate value.
    """
    lead.opportunity_score = result.get("opportunity_score")
    lead.opportunity_reasons = result.get("opportunity_reasons") or []
    lead.site_analysis = result.get("site_analysis") or {}

    social = result.get("social_profiles") or {}
    lead.social_profiles = social if isinstance(social, dict) else {}

    lead.tech_stack = result.get("tech_stack") or []
    lead.enrichment_sources = result.get("enrichment_sources") or []

    lead.score_acessibilidade = result.get("score_acessibilidade", 0)
    lead.score_lp = result.get("score_lp", 0)
    lead.score_automacao = result.get("score_automacao", 0)
    lead.score_mapa = result.get("score_mapa", 0)
    lead.nivel_recomendado = result.get("nivel_recomendado")

    if result.get("email"):
        lead.email = result["email"]
    if result.get("cnpj"):
        lead.cnpj = result["cnpj"]
    if result.get("razao_social"):
        lead.razao_social = result["razao_social"]
    if result.get("porte"):
        lead.porte = result["porte"]
    if result.get("cnae"):
        lead.cnae = result["cnae"]
    if result.get("data_fundacao"):
        try:
            lead.data_fundacao = datetime.fromisoformat(
                result["data_fundacao"]
            ).date()
        except (ValueError, TypeError):
            pass
    if result.get("socios"):
        lead.socios = result["socios"]
    if result.get("website") and not lead.website:
        lead.website = result["website"]
    # Tratamento formal (PR3.2) — preserve manual override if already set.
    if result.get("tratamento_formal") and not getattr(lead, "tratamento_formal", None):
        lead.tratamento_formal = result["tratamento_formal"]

    for attr in (
        "perfil_lead",
        "nicho_canonico",
        "nicho_source",
        "nicho_confidence",
        "pacote_sugerido",
        "prioridade",
        "classification_hash",
    ):
        if attr in result and result[attr] is not None:
            setattr(lead, attr, result[attr])

    if result.get("perfil_lead") is not None:
        lead.classified_at = datetime.utcnow()
