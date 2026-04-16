"""CNAE and IBGE lookups for CNPJ-based lead discovery.

niche_to_cnaes(niche) -> list[str]   — niche text to CNAE code(s)
city_to_ibge(city)    -> tuple[str, str] | None  — "Chapecó SC" -> ("4204202", "SC")
"""
from __future__ import annotations

import re
import unicodedata
import logging

import requests

logger = logging.getLogger(__name__)

# ── CNAE mapping ──────────────────────────────────────────────────────────────
# Keys are lowercase niche labels (pt-BR). Values are CNAE codes (digits only).
_CNAE_MAP: dict[str, list[str]] = {
    # Saúde
    "dentista": ["8630504"],
    "odontologia": ["8630504"],
    "clinica odontologica": ["8630504"],
    "medico": ["8630503"],
    "clinica medica": ["8630503"],
    "psicologo": ["8650004"],
    "psicologia": ["8650004"],
    "fisioterapia": ["8650001"],
    "fisioterapeuta": ["8650001"],
    "nutricionista": ["8650003"],
    "fonoaudiologia": ["8650002"],
    "veterinaria": ["7500100"],
    "pet shop": ["4789004", "7500100"],
    "farmacia": ["4771701", "4771702"],
    "drogaria": ["4771701"],
    "laboratorio": ["8640202"],
    "clinica": ["8630503", "8630504"],
    # Beleza
    "salao de beleza": ["9602501"],
    "cabeleireiro": ["9602501"],
    "barbearia": ["9602501"],
    "estetica": ["9602502"],
    "manicure": ["9602501"],
    "spa": ["9602502"],
    # Fitness
    "academia": ["9313100"],
    "fitness": ["9313100"],
    "pilates": ["9313100"],
    "crossfit": ["9313100"],
    # Alimentação
    "restaurante": ["5611201", "5611203"],
    "lanchonete": ["5611201"],
    "padaria": ["1091101", "4712100"],
    "pizzaria": ["5611201"],
    "cafeteria": ["5611205"],
    "sorveteria": ["5611205"],
    "bar": ["5611204"],
    # Educação
    "escola": ["8511200", "8512100"],
    "creche": ["8511200"],
    "curso": ["8599604"],
    "idiomas": ["8599604"],
    # Serviços profissionais
    "advogado": ["6911701"],
    "escritorio de advocacia": ["6911701"],
    "contabilidade": ["6920601"],
    "contador": ["6920601"],
    "imobiliaria": ["6810201", "6810202"],
    "agencia de publicidade": ["7311400"],
    "marketing digital": ["7311400"],
    "agencia digital": ["7311400"],
    # Automotivo
    "oficina": ["4520001", "4520002"],
    "mecanica": ["4520001"],
    "funilaria": ["4520003"],
    "lavagem de carro": ["4529101"],
    # Construção
    "construcao": ["4120400"],
    "engenharia": ["7112000"],
    "arquitetura": ["7111100"],
    # Hospedagem
    "hotel": ["5510801"],
    "pousada": ["5510801"],
    "hostel": ["5510802"],
    # Varejo
    "supermercado": ["4711301", "4711302"],
    "mercado": ["4712100"],
    # TI
    "desenvolvimento de software": ["6209100"],
    "ti": ["6209100"],
    "suporte de informatica": ["6209100"],
}

_UF_CODES = frozenset({
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
    "RO", "RR", "RS", "SC", "SE", "SP", "TO",
})

# Module-level cache: uf -> list of {nome, codigo_ibge}
_IBGE_CACHE: dict[str, list[dict]] = {}


# ── Public API ────────────────────────────────────────────────────────────────

def niche_to_cnaes(niche: str) -> list[str]:
    """Map niche text to CNAE code list.  Returns [] if no match."""
    normalized = _normalize(niche)

    if normalized in _CNAE_MAP:
        return list(_CNAE_MAP[normalized])

    # Partial: normalized is substring of a key or vice versa
    results: list[str] = []
    seen: set[str] = set()
    for key, codes in _CNAE_MAP.items():
        if normalized in key or key in normalized:
            for c in codes:
                if c not in seen:
                    seen.add(c)
                    results.append(c)

    return results


def city_to_ibge(city: str) -> tuple[str, str] | None:
    """Resolve city name (optionally with UF) to (ibge_code, uf).

    Accepts: "Chapecó SC", "São Paulo - SP", "Florianópolis"
    Returns None when city cannot be resolved.
    """
    city_name = city.strip()
    uf: str | None = None

    # Extract UF from end of string: "Chapecó SC" or "Chapecó - SC"
    match = re.search(r"[\s\-–]+([A-Za-z]{2})\s*$", city_name)
    if match and match.group(1).upper() in _UF_CODES:
        uf = match.group(1).upper()
        city_name = city_name[: match.start()].strip()

    if uf:
        return _find_in_state(city_name, uf)

    # No UF given — search all states (slower)
    for state in sorted(_UF_CODES):
        result = _find_in_state(city_name, state)
        if result:
            return result

    return None


# ── Internals ─────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Lowercase + strip accents."""
    nfkd = unicodedata.normalize("NFKD", text.lower().strip())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _find_in_state(city_name: str, uf: str) -> tuple[str, str] | None:
    municipalities = _get_municipalities(uf)
    if not municipalities:
        return None
    normalized = _normalize(city_name)
    for mun in municipalities:
        if _normalize(mun.get("nome", "")) == normalized:
            return str(mun["codigo_ibge"]), uf
    return None


def _get_municipalities(uf: str) -> list[dict]:
    """Fetch (and cache) municipalities for a state from BrasilAPI."""
    if uf in _IBGE_CACHE:
        return _IBGE_CACHE[uf]
    try:
        resp = requests.get(
            f"https://brasilapi.com.br/api/ibge/municipios/v1/{uf}",
            timeout=10,
        )
        if resp.status_code == 200:
            _IBGE_CACHE[uf] = resp.json()
            return _IBGE_CACHE[uf]
        logger.warning("BrasilAPI municipalities returned %s for UF %s", resp.status_code, uf)
    except Exception as exc:
        logger.warning("BrasilAPI municipalities request failed for UF %s: %s", uf, exc)
    return []
