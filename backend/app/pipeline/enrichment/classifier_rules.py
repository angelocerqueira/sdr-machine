"""Thresholds and aliases for lead classification — externalized for tuning."""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from app.pipeline.enrichment.classifier_enums import (
    LeadProfile, NichoCanonico, PacoteSugerido, Prioridade,
)


# Profile cascade thresholds
PROFILE_THRESHOLDS: dict[str, float | int] = {
    "disqualified_min_rating": 3.0,
    "disqualified_min_reviews_without_phone": 3,
    "hot_no_site_min_rating": 4.0,
    "hot_no_site_min_reviews": 30,
    "hot_bad_site_min_score": 60,
    "hot_bad_site_min_reviews_when_no_instagram": 30,
    "cold_max_score": 20,
}

# Mapping perfil → (pacote_sugerido, prioridade)
PROFILE_TO_DERIVED: dict[LeadProfile, tuple[PacoteSugerido, Prioridade]] = {
    LeadProfile.HOT_NO_SITE: (PacoteSugerido.ESSENCIAL, Prioridade.MAXIMA),
    LeadProfile.HOT_BAD_SITE: (PacoteSugerido.PROFISSIONAL, Prioridade.ALTA),
    LeadProfile.WARM: (PacoteSugerido.ESSENCIAL, Prioridade.MEDIA),
    LeadProfile.COLD: (PacoteSugerido.SKIP, Prioridade.BAIXA),
    LeadProfile.DISQUALIFIED: (PacoteSugerido.SKIP, Prioridade.PULAR),
}

# Curated aliases for each bucket (lowercased keywords)
NICHO_ALIASES: dict[NichoCanonico, list[str]] = {
    NichoCanonico.DENTISTA: [
        "dentist", "dentista", "odonto", "odontolog", "clinica odontologica",
        "sorriso", "ortodontia", "implante dentario", "dental",
    ],
    NichoCanonico.ESTETICA: [
        "estetica", "dermato", "dermatologia", "harmonizacao",
        "botox", "preenchimento", "clinica de estetica", "estetica facial",
    ],
    NichoCanonico.SALAO_BARBEARIA: [
        "salao de beleza", "barbearia", "barber", "cabeleireiro",
        "manicure", "pedicure", "escova",
    ],
    NichoCanonico.RESTAURANTE: [
        "restaurante", "bar", "pizzaria", "lanchonete", "churrascaria",
        "pizza", "hamburgueria", "padaria",
    ],
    NichoCanonico.PETSHOP_VET: [
        "pet shop", "petshop", "veterinaria", "clinica veterinaria",
        "banho e tosa", "pet",
    ],
    NichoCanonico.ACADEMIA: [
        "academia", "crossfit", "pilates", "muay thai", "jiu jitsu",
        "box fitness", "yoga",
    ],
    NichoCanonico.CONTABILIDADE: [
        "contabilidade", "contador", "escritorio contabil", "contabil",
    ],
    NichoCanonico.IMOBILIARIA: [
        "imobiliaria", "corretor de imoveis", "venda de imoveis",
        "apartamentos", "casas",
    ],
    NichoCanonico.LOJA_ROUPAS: [
        "loja de roupas", "boutique", "moda", "confeccao",
        "loja feminina", "loja masculina",
    ],
    NichoCanonico.AUTO_ESCOLA: [
        "auto escola", "autoescola", "cfc", "escola de direcao",
    ],
    NichoCanonico.ADVOCACIA: [
        "advocacia", "advogado", "advogada", "escritorio de advocacia",
        "juridico",
    ],
    NichoCanonico.INDUSTRIA: [
        "industria", "fabrica", "manufatura", "industrial",
    ],
    NichoCanonico.CLINICA_MEDICA: [
        "clinica medica", "medico", "consultorio medico", "cardiologia",
        "ginecologia", "pediatria",
    ],
    NichoCanonico.ESCOLA_CURSO: [
        "escola", "curso", "idiomas", "ingles", "espanhol", "cursinho",
        "preparatorio",
    ],
}

FUZZY_MATCH_THRESHOLD = 0.75


def _normalize(s: str | None) -> str:
    if not s:
        return ""
    # NFKD + strip combining marks → diacritic folding
    nfkd = unicodedata.normalize("NFKD", s)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return stripped.strip().lower()


def fuzzy_match_nicho(raw: str | None) -> tuple[NichoCanonico, float] | None:
    """Keyword + difflib matching against NICHO_ALIASES.

    Returns (bucket, confidence) on match, None otherwise. Never raises.
    """
    text = _normalize(raw)
    if not text:
        return None

    best: tuple[NichoCanonico, float] | None = None
    for bucket, aliases in NICHO_ALIASES.items():
        for alias in aliases:
            alias_norm = _normalize(alias)
            if not alias_norm:
                continue
            # Long aliases (>=4 chars): substring match at confidence 1.0
            if len(alias_norm) >= 4 and alias_norm in text:
                return (bucket, 1.0)
            # Short aliases (<4 chars): require word boundary match
            if len(alias_norm) < 4:
                if re.search(rf"\b{re.escape(alias_norm)}\b", text):
                    return (bucket, 1.0)
                continue  # don't run fuzzy on short aliases — ratio too noisy
            # Fuzzy ratio on longer aliases
            ratio = SequenceMatcher(None, alias_norm, text).ratio()
            if ratio >= FUZZY_MATCH_THRESHOLD:
                if best is None or ratio > best[1]:
                    best = (bucket, ratio)
    return best
