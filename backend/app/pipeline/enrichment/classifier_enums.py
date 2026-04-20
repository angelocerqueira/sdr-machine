"""Enums for lead profile classification."""
from enum import Enum


class LeadProfile(str, Enum):
    HOT_NO_SITE = "hot_no_site"
    HOT_BAD_SITE = "hot_bad_site"
    WARM = "warm"
    COLD = "cold"
    DISQUALIFIED = "disqualified"


class NichoCanonico(str, Enum):
    DENTISTA = "dentista"
    ESTETICA = "estetica"
    SALAO_BARBEARIA = "salao_barbearia"
    RESTAURANTE = "restaurante"
    PETSHOP_VET = "petshop_vet"
    ACADEMIA = "academia"
    CONTABILIDADE = "contabilidade"
    IMOBILIARIA = "imobiliaria"
    LOJA_ROUPAS = "loja_roupas"
    AUTO_ESCOLA = "auto_escola"
    ADVOCACIA = "advocacia"
    INDUSTRIA = "industria"
    CLINICA_MEDICA = "clinica_medica"
    ESCOLA_CURSO = "escola_curso"
    OUTROS = "outros"


class NichoSource(str, Enum):
    APIFY_CATEGORY = "apify_category"
    FUZZY_MATCH = "fuzzy_match"
    LLM_INFERRED = "llm_inferred"
    MANUAL = "manual"
    FAILED = "failed"


class PacoteSugerido(str, Enum):
    ESSENCIAL = "essencial"
    PROFISSIONAL = "profissional"
    PREMIUM = "premium"
    SKIP = "skip"


class Prioridade(str, Enum):
    MAXIMA = "maxima"
    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"
    PULAR = "pular"
