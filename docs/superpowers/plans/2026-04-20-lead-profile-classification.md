# Lead Profile Classification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Classificar cada lead em 5 perfis (HOT_NO_SITE, HOT_BAD_SITE, WARM, COLD, DISQUALIFIED) + 15 nichos canônicos para priorização no kanban, escolha de pacote, segmentação de outreach e benchmark futuro por nicho × cidade.

**Architecture:** Módulo puro `classifier.py` (regras determinísticas de perfil + 3-camada fuzzy→LLM para nicho) consumido por um novo `ClassificationProvider` (integrado à cadeia de providers existente) **e** por um endpoint standalone `POST /api/pipeline/classify` (batch job com SSE). Resultado: 9 campos novos no `Lead`, exibidos e filtráveis no frontend.

**Tech Stack:** FastAPI 0.115 · SQLAlchemy 2.0 · PostgreSQL 16 · Alembic · Pydantic · Anthropic SDK · tenacity (retry) · Next.js 16 · React 19 · TypeScript · Tailwind 4 · sse-starlette

**Reference:** `docs/superpowers/specs/2026-04-20-lead-profile-classification-design.md`

---

## File Structure

### Backend — novos arquivos

| Arquivo | Responsabilidade |
|---|---|
| `backend/app/pipeline/enrichment/classifier.py` | Função pura `classify()` + `ClassificationResult` dataclass |
| `backend/app/pipeline/enrichment/classifier_rules.py` | Thresholds + aliases de nicho (externalizados pra tuning) |
| `backend/app/pipeline/enrichment/classifier_prompts.py` | Prompt do LLM + exemplos few-shot |
| `backend/app/pipeline/enrichment/providers/classification_provider.py` | `ClassificationProvider` (integra no orchestrator) |
| `backend/alembic/versions/k04_lead_classification.py` | Migration: 9 campos novos no Lead |
| `backend/tests/test_classifier.py` | Unit tests da função pura |
| `backend/tests/test_classifier_rules.py` | Unit tests de fuzzy matching |
| `backend/tests/test_classification_provider.py` | Integration tests do provider |
| `backend/tests/test_classify_job.py` | Integration tests do batch job |
| `backend/tests/test_classification_resilience.py` | E2E resilience tests |

### Backend — arquivos modificados

| Arquivo | O que muda |
|---|---|
| `backend/app/models.py` | Adicionar 9 campos novos no `Lead` |
| `backend/app/schemas.py` | Adicionar campos aos schemas `LeadOut`, `LeadSummaryOut`, novos schemas `ClassifyRequest`, `ReclassifyRequest` |
| `backend/app/pipeline/scraper.py` | Extrair `has_instagram` do payload Apify ao criar Lead |
| `backend/app/pipeline/enrichment/orchestrator.py` | Adicionar `"classification"` ao `_PHASE_ORDER` e `optimistic_names` |
| `backend/app/pipeline/enricher.py` | Persistir os 9 campos novos após `orchestrator.run()` |
| `backend/app/routers/pipeline.py` | Adicionar `POST /api/pipeline/classify` + `_run_classify()` + chain após csv-import |
| `backend/app/routers/leads.py` | Adicionar `POST /api/leads/{id}/reclassify` + `GET /api/leads/review` + filtros por perfil/nicho |
| `backend/requirements.txt` | Adicionar `tenacity>=8.2` |

### Frontend — novos arquivos

| Arquivo | Responsabilidade |
|---|---|
| `frontend/src/components/ui/profile-badge.tsx` | Badge reutilizável pra perfil |
| `frontend/src/components/leads/la-classification.tsx` | Seção "Classificação" no rail |
| `frontend/src/components/dashboard/profile-distribution.tsx` | Widget distribuição de perfis |
| `frontend/src/components/dashboard/nicho-distribution.tsx` | Widget distribuição de nichos |
| `frontend/src/components/pipeline/classify-modal.tsx` | Modal do botão "Classificar backlog" |
| `frontend/src/app/app/leads/review/page.tsx` | Página de revisão de nichos |
| `frontend/src/app/app/leads/review/review-table.tsx` | Tabela client-side da revisão |

### Frontend — arquivos modificados

| Arquivo | O que muda |
|---|---|
| `frontend/src/lib/types.ts` | Adicionar `perfil_lead`, `nicho_canonico`, etc ao type `Lead`; novos enums |
| `frontend/src/lib/api.ts` | Métodos `classifyLeads`, `reclassifyLead`, `getLeadsForReview` |
| `frontend/src/components/kanban-board.tsx` | Render `<ProfileBadge>` no card |
| `frontend/src/components/kanban-filters.tsx` | Dropdowns de perfil e nicho |
| `frontend/src/components/leads/la-header.tsx` | Badge de perfil no header |
| `frontend/src/components/leads/la-rail.tsx` | Embed `<LaClassification>` |
| `frontend/src/components/leads/la-master.tsx` | Filtros de perfil/nicho |
| `frontend/src/components/pipeline-controls.tsx` | Botão "Classificar" + integração do modal |
| `frontend/src/components/app-sidebar.tsx` | Link "Revisão de nichos" com contador |
| `frontend/src/app/app/dashboard/page.tsx` | Inserir os 2 widgets novos no grid |

---

## Fase 1 — Backend foundation (enums + migration + classifier puro)

### Task 1: Adicionar dependências

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Adicionar linha ao `requirements.txt`**

Abrir `backend/requirements.txt` e acrescentar ao final:

```
tenacity>=8.2.0
```

- [ ] **Step 2: Instalar no venv**

Run:
```bash
cd backend && .venv/bin/pip install tenacity
```

Expected: install success + `Successfully installed tenacity-...`

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add tenacity for retry with backoff"
```

---

### Task 2: Criar enums de classificação

**Files:**
- Create: `backend/app/pipeline/enrichment/classifier_enums.py`
- Test: `backend/tests/test_classifier_enums.py`

- [ ] **Step 1: Escrever testes primeiro**

Criar `backend/tests/test_classifier_enums.py`:

```python
from app.pipeline.enrichment.classifier_enums import (
    LeadProfile, NichoCanonico, NichoSource, PacoteSugerido, Prioridade,
)


def test_all_enums_are_string_enums():
    assert LeadProfile.HOT_NO_SITE.value == "hot_no_site"
    assert LeadProfile.HOT_BAD_SITE.value == "hot_bad_site"
    assert LeadProfile.WARM.value == "warm"
    assert LeadProfile.COLD.value == "cold"
    assert LeadProfile.DISQUALIFIED.value == "disqualified"


def test_nicho_canonico_has_15_buckets():
    assert len(list(NichoCanonico)) == 15
    assert NichoCanonico.OUTROS.value == "outros"


def test_nicho_source_values():
    expected = {"apify_category", "fuzzy_match", "llm_inferred", "manual", "failed"}
    assert {s.value for s in NichoSource} == expected


def test_pacote_sugerido_values():
    expected = {"essencial", "profissional", "premium", "skip"}
    assert {p.value for p in PacoteSugerido} == expected


def test_prioridade_values():
    expected = {"maxima", "alta", "media", "baixa", "pular"}
    assert {p.value for p in Prioridade} == expected
```

- [ ] **Step 2: Rodar teste (fail)**

Run: `cd backend && pytest tests/test_classifier_enums.py -v`
Expected: FAIL com `ModuleNotFoundError` (arquivo ainda não existe)

- [ ] **Step 3: Implementar enums**

Criar `backend/app/pipeline/enrichment/classifier_enums.py`:

```python
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
```

- [ ] **Step 4: Rodar teste (pass)**

Run: `cd backend && pytest tests/test_classifier_enums.py -v`
Expected: 5 tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/enrichment/classifier_enums.py backend/tests/test_classifier_enums.py
git commit -m "feat(classification): add enums for lead profile and nicho canonico"
```

---

### Task 3: Escrever regras externalizadas (thresholds + aliases)

**Files:**
- Create: `backend/app/pipeline/enrichment/classifier_rules.py`
- Test: `backend/tests/test_classifier_rules.py`

- [ ] **Step 1: Escrever testes primeiro**

Criar `backend/tests/test_classifier_rules.py`:

```python
from app.pipeline.enrichment.classifier_enums import NichoCanonico
from app.pipeline.enrichment.classifier_rules import (
    NICHO_ALIASES, PROFILE_THRESHOLDS, PROFILE_TO_DERIVED, fuzzy_match_nicho,
)


def test_aliases_cover_all_15_buckets():
    assert set(NICHO_ALIASES.keys()) == {n for n in NichoCanonico if n != NichoCanonico.OUTROS}


def test_fuzzy_match_obvious_cases():
    assert fuzzy_match_nicho("Dentist") == (NichoCanonico.DENTISTA, 1.0)
    assert fuzzy_match_nicho("Clinica Odontologica Dr Silva") == (NichoCanonico.DENTISTA, 1.0)
    assert fuzzy_match_nicho("Pizzaria da Nonna") == (NichoCanonico.RESTAURANTE, 1.0)


def test_fuzzy_match_misspelled_returns_lower_confidence():
    bucket, conf = fuzzy_match_nicho("odontologia")
    assert bucket == NichoCanonico.DENTISTA
    assert conf >= 0.75


def test_fuzzy_match_returns_none_when_no_match():
    assert fuzzy_match_nicho("Consultoria de Fusões e Aquisições") is None


def test_fuzzy_match_handles_empty():
    assert fuzzy_match_nicho("") is None
    assert fuzzy_match_nicho(None) is None


def test_profile_thresholds_keys():
    assert "hot_no_site_min_rating" in PROFILE_THRESHOLDS
    assert "hot_no_site_min_reviews" in PROFILE_THRESHOLDS
    assert "hot_bad_site_min_score" in PROFILE_THRESHOLDS
    assert "cold_max_score" in PROFILE_THRESHOLDS
    assert "disqualified_min_rating" in PROFILE_THRESHOLDS


def test_profile_to_derived_complete():
    from app.pipeline.enrichment.classifier_enums import LeadProfile
    for profile in LeadProfile:
        assert profile in PROFILE_TO_DERIVED
        pacote, prioridade = PROFILE_TO_DERIVED[profile]
        assert pacote is not None
        assert prioridade is not None
```

- [ ] **Step 2: Rodar teste (fail)**

Run: `cd backend && pytest tests/test_classifier_rules.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Implementar regras**

Criar `backend/app/pipeline/enrichment/classifier_rules.py`:

```python
"""Thresholds and aliases for lead classification — externalized for tuning."""
from __future__ import annotations

from difflib import SequenceMatcher

from app.pipeline.enrichment.classifier_enums import (
    LeadProfile, NichoCanonico, PacoteSugerido, Prioridade,
)


# Profile cascade thresholds
PROFILE_THRESHOLDS: dict = {
    "disqualified_min_rating": 3.0,
    "disqualified_min_reviews_without_phone": 3,
    "hot_no_site_min_rating": 4.0,
    "hot_no_site_min_reviews": 30,
    "hot_bad_site_min_score": 60,
    "hot_bad_site_min_reviews_when_no_instagram": 30,
    "cold_max_score": 20,
}

# Mapping perfil → (pacote_sugerido, prioridade)
PROFILE_TO_DERIVED: dict = {
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


def _normalize(s: str) -> str:
    return (s or "").strip().lower()


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
            # Exact substring match → confidence 1.0
            if alias in text:
                return (bucket, 1.0)
            # Fuzzy ratio
            ratio = SequenceMatcher(None, alias, text).ratio()
            if ratio >= FUZZY_MATCH_THRESHOLD:
                if best is None or ratio > best[1]:
                    best = (bucket, ratio)
    return best
```

- [ ] **Step 4: Rodar teste (pass)**

Run: `cd backend && pytest tests/test_classifier_rules.py -v`
Expected: 7 tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/enrichment/classifier_rules.py backend/tests/test_classifier_rules.py
git commit -m "feat(classification): add externalized rules and fuzzy matching"
```

---

### Task 4: LLM prompt para nicho (sem call ainda)

**Files:**
- Create: `backend/app/pipeline/enrichment/classifier_prompts.py`
- Test: `backend/tests/test_classifier_prompts.py`

- [ ] **Step 1: Escrever teste primeiro**

Criar `backend/tests/test_classifier_prompts.py`:

```python
from app.pipeline.enrichment.classifier_prompts import (
    build_nicho_prompt, NICHO_TOOL_SCHEMA,
)


def test_prompt_mentions_all_15_buckets():
    prompt = build_nicho_prompt(
        nome="Teste", nicho_raw="foo", descricao="", reviews=[]
    )
    for bucket in [
        "dentista", "estetica", "salao_barbearia", "restaurante",
        "petshop_vet", "academia", "contabilidade", "imobiliaria",
        "loja_roupas", "auto_escola", "advocacia", "industria",
        "clinica_medica", "escola_curso", "outros",
    ]:
        assert bucket in prompt


def test_prompt_includes_input_data():
    prompt = build_nicho_prompt(
        nome="Clínica Sorriso",
        nicho_raw="Dentist",
        descricao="Atendimento odontológico completo",
        reviews=["Ótimo dentista!"],
    )
    assert "Clínica Sorriso" in prompt
    assert "Dentist" in prompt
    assert "odontológico" in prompt
    assert "Ótimo dentista!" in prompt


def test_prompt_truncates_reviews_to_3():
    long = ["r" + str(i) for i in range(10)]
    prompt = build_nicho_prompt(
        nome="X", nicho_raw="Y", descricao="", reviews=long
    )
    assert "r0" in prompt
    assert "r2" in prompt
    assert "r3" not in prompt


def test_tool_schema_enum_has_15_values():
    enum = NICHO_TOOL_SCHEMA["input_schema"]["properties"]["nicho_canonico"]["enum"]
    assert len(enum) == 15
    assert "outros" in enum
```

- [ ] **Step 2: Rodar (fail)**

Run: `cd backend && pytest tests/test_classifier_prompts.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Implementar**

Criar `backend/app/pipeline/enrichment/classifier_prompts.py`:

```python
"""Prompt and tool-use schema for nicho inference via LLM."""
from __future__ import annotations

from app.pipeline.enrichment.classifier_enums import NichoCanonico


NICHO_TOOL_SCHEMA = {
    "name": "classify_nicho",
    "description": (
        "Classifica o negócio em um dos 15 buckets canônicos de nicho. "
        "Use 'outros' apenas se nenhum bucket se encaixar minimamente."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "nicho_canonico": {
                "type": "string",
                "enum": [n.value for n in NichoCanonico],
                "description": "Bucket canônico do nicho",
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Confiança da classificação (0-1)",
            },
            "reasoning": {
                "type": "string",
                "description": "Justificativa curta (1 frase)",
            },
        },
        "required": ["nicho_canonico", "confidence", "reasoning"],
    },
}


_FEW_SHOT = """Exemplos:

Entrada: Nome="Clinica Sorriso", nicho_raw="Dentist", descricao="Odontologia geral"
Saída: dentista | 0.98 | Clínica odontológica explícita

Entrada: Nome="Bella Estética", nicho_raw="Beauty Salon", descricao="Harmonização facial"
Saída: estetica | 0.90 | Harmonização facial é estética, não salão

Entrada: Nome="Consultoria ACME", nicho_raw="", descricao="Consultoria empresarial B2B"
Saída: outros | 0.95 | Consultoria não tem bucket específico
"""


def build_nicho_prompt(
    *,
    nome: str,
    nicho_raw: str | None,
    descricao: str | None,
    reviews: list[str] | None,
) -> str:
    """Build the user-turn prompt for the nicho classifier."""
    sample_reviews = (reviews or [])[:3]
    reviews_block = "\n".join(f"- {r}" for r in sample_reviews) if sample_reviews else "(nenhuma)"

    return (
        "Você é um classificador de nichos de negócios brasileiros.\n"
        "Buckets permitidos: "
        + ", ".join(n.value for n in NichoCanonico)
        + "\n\n"
        + _FEW_SHOT
        + "\n"
        + "Classifique o seguinte negócio. Use 'outros' apenas se nenhum bucket se encaixar.\n\n"
        + f"Nome: {nome or '(vazio)'}\n"
        + f"Nicho bruto: {nicho_raw or '(vazio)'}\n"
        + f"Descrição: {descricao or '(vazia)'}\n"
        + f"Amostra de reviews:\n{reviews_block}\n"
    )
```

- [ ] **Step 4: Rodar (pass)**

Run: `cd backend && pytest tests/test_classifier_prompts.py -v`
Expected: 4 tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/enrichment/classifier_prompts.py backend/tests/test_classifier_prompts.py
git commit -m "feat(classification): add LLM prompt and tool schema for nicho"
```

---

### Task 5: Função `classify()` — regras de perfil

**Files:**
- Create: `backend/app/pipeline/enrichment/classifier.py`
- Test: `backend/tests/test_classifier.py`

Nesta task implementamos **apenas o perfil** (regras determinísticas). Nicho vira stub que sempre retorna `OUTROS/failed`. Próxima task conecta o LLM.

- [ ] **Step 1: Escrever testes de perfil**

Criar `backend/tests/test_classifier.py`:

```python
import pytest

from app.pipeline.enrichment.classifier import classify, ClassificationResult
from app.pipeline.enrichment.classifier_enums import (
    LeadProfile, NichoCanonico, NichoSource, PacoteSugerido, Prioridade,
)


def _base_lead(**overrides) -> dict:
    """Lead minimally valid to pass DISQUALIFIED gate."""
    base = {
        "has_website": True, "score": 40,
        "rating": 4.0, "review_count": 20,
        "has_ssl": False, "has_analytics": False,
        "has_chatbot": False, "has_whatsapp_cta": False,
        "has_instagram": False,
        "nicho_raw": "qualquer coisa",
        "nome": "Lead Teste", "descricao": "", "reviews": [],
        "telefone": "11999999999",
    }
    base.update(overrides)
    return base


def test_returns_classification_result_type():
    result = classify(_base_lead())
    assert isinstance(result, ClassificationResult)


def test_disqualified_rating_below_threshold():
    result = classify(_base_lead(rating=2.5))
    assert result.perfil_lead == LeadProfile.DISQUALIFIED


def test_disqualified_no_phone_and_few_reviews():
    result = classify(_base_lead(telefone=None, review_count=1))
    assert result.perfil_lead == LeadProfile.DISQUALIFIED


def test_hot_no_site():
    result = classify(_base_lead(
        has_website=False, rating=4.5, review_count=80,
    ))
    assert result.perfil_lead == LeadProfile.HOT_NO_SITE
    assert result.pacote_sugerido == PacoteSugerido.ESSENCIAL
    assert result.prioridade == Prioridade.MAXIMA


def test_hot_bad_site_with_instagram():
    result = classify(_base_lead(
        has_website=True, score=72, has_instagram=True, review_count=5,
    ))
    assert result.perfil_lead == LeadProfile.HOT_BAD_SITE


def test_hot_bad_site_without_instagram_many_reviews():
    result = classify(_base_lead(
        has_website=True, score=72, has_instagram=False, review_count=60,
    ))
    assert result.perfil_lead == LeadProfile.HOT_BAD_SITE


def test_not_hot_bad_site_if_score_too_low():
    result = classify(_base_lead(
        has_website=True, score=50, has_instagram=True,
    ))
    # 50 < 60 → não HOT_BAD_SITE; cai em WARM
    assert result.perfil_lead == LeadProfile.WARM


def test_cold_site():
    result = classify(_base_lead(
        has_website=True, score=10,
        has_ssl=True, has_analytics=True, has_chatbot=True,
    ))
    assert result.perfil_lead == LeadProfile.COLD
    assert result.pacote_sugerido == PacoteSugerido.SKIP
    assert result.prioridade == Prioridade.BAIXA


def test_warm_catch_all():
    result = classify(_base_lead(
        has_website=True, score=35, has_analytics=True,
    ))
    assert result.perfil_lead == LeadProfile.WARM


def test_missing_score_defaults_to_warm():
    result = classify(_base_lead(has_website=True, score=None))
    # Default score=50 → catch-all WARM
    assert result.perfil_lead == LeadProfile.WARM


def test_missing_rating_and_reviews_disqualifies():
    result = classify(_base_lead(
        rating=None, review_count=None, telefone=None,
    ))
    assert result.perfil_lead == LeadProfile.DISQUALIFIED


def test_missing_has_website_treated_as_false():
    # Ausência de site, mas rating/reviews alto → HOT_NO_SITE
    result = classify(_base_lead(
        has_website=None, rating=4.5, review_count=50,
    ))
    assert result.perfil_lead == LeadProfile.HOT_NO_SITE


def test_classification_hash_is_deterministic():
    data = _base_lead()
    r1 = classify(data)
    r2 = classify(data)
    assert r1.classification_hash == r2.classification_hash


def test_classification_hash_changes_when_key_field_changes():
    r1 = classify(_base_lead(score=40))
    r2 = classify(_base_lead(score=70))
    assert r1.classification_hash != r2.classification_hash


def test_never_raises_on_empty_input():
    result = classify({})
    assert isinstance(result, ClassificationResult)
    assert result.perfil_lead == LeadProfile.DISQUALIFIED


def test_never_raises_on_garbage_types():
    result = classify({
        "score": "not-a-number",
        "rating": [],
        "review_count": {"wat": 1},
        "has_website": "yes",
    })
    assert isinstance(result, ClassificationResult)
```

Property-based test (opcional mas recomendado):

```python
from hypothesis import given, strategies as st


@given(st.dictionaries(st.text(), st.one_of(
    st.none(), st.integers(), st.floats(allow_nan=False), st.text(),
    st.booleans(), st.lists(st.text()),
)))
def test_classify_never_raises(arbitrary_input):
    result = classify(arbitrary_input)
    assert isinstance(result, ClassificationResult)
```

- [ ] **Step 2: Rodar (fail)**

Run: `cd backend && pytest tests/test_classifier.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Implementar `classify()` com perfil + stub nicho**

Criar `backend/app/pipeline/enrichment/classifier.py`:

```python
"""Pure classification function — no DB, no I/O dependencies.

Never raises: every failure mode lowers confidence or returns a safe
fallback (DISQUALIFIED / OUTROS / failed). See spec section 7.1.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, asdict
from typing import Any

from app.pipeline.enrichment.classifier_enums import (
    LeadProfile, NichoCanonico, NichoSource, PacoteSugerido, Prioridade,
)
from app.pipeline.enrichment.classifier_rules import (
    PROFILE_THRESHOLDS, PROFILE_TO_DERIVED, fuzzy_match_nicho,
)

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    perfil_lead: LeadProfile
    nicho_canonico: NichoCanonico
    nicho_source: NichoSource
    nicho_confidence: float
    pacote_sugerido: PacoteSugerido
    prioridade: Prioridade
    classification_hash: str
    error_reason: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        # Convert enums to their string values
        for k in (
            "perfil_lead", "nicho_canonico", "nicho_source",
            "pacote_sugerido", "prioridade",
        ):
            d[k] = d[k].value if hasattr(d[k], "value") else d[k]
        return d


# Defaults for missing inputs
_DEFAULTS = {
    "has_website": False,
    "score": 50,
    "rating": 0.0,
    "review_count": 0,
    "has_ssl": False,
    "has_analytics": False,
    "has_chatbot": False,
    "has_whatsapp_cta": False,
    "has_instagram": False,
}


def _coerce_num(v: Any, default: float) -> float:
    if v is None:
        return default
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _coerce_bool(v: Any, default: bool) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "sim", "t")
    return default


def _compute_hash(lead_data: dict) -> str:
    key = "|".join([
        str(_coerce_bool(lead_data.get("has_website"), _DEFAULTS["has_website"])),
        str(_coerce_num(lead_data.get("score"), _DEFAULTS["score"])),
        str(_coerce_num(lead_data.get("rating"), _DEFAULTS["rating"])),
        str(_coerce_num(lead_data.get("review_count"), _DEFAULTS["review_count"])),
        str(_coerce_bool(lead_data.get("has_ssl"), False)),
        str(_coerce_bool(lead_data.get("has_analytics"), False)),
        str(_coerce_bool(lead_data.get("has_chatbot"), False)),
        str(_coerce_bool(lead_data.get("has_instagram"), False)),
        str(lead_data.get("nicho_raw") or ""),
        str(lead_data.get("nome") or ""),
    ])
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def _classify_profile(lead_data: dict) -> LeadProfile:
    """Cascade of deterministic rules — first match wins. Never raises."""
    has_website = _coerce_bool(lead_data.get("has_website"), _DEFAULTS["has_website"])
    score = _coerce_num(lead_data.get("score"), _DEFAULTS["score"])
    rating = _coerce_num(lead_data.get("rating"), _DEFAULTS["rating"])
    review_count = _coerce_num(lead_data.get("review_count"), _DEFAULTS["review_count"])
    has_ssl = _coerce_bool(lead_data.get("has_ssl"), False)
    has_analytics = _coerce_bool(lead_data.get("has_analytics"), False)
    has_chatbot = _coerce_bool(lead_data.get("has_chatbot"), False)
    has_whatsapp_cta = _coerce_bool(lead_data.get("has_whatsapp_cta"), False)
    has_instagram = _coerce_bool(lead_data.get("has_instagram"), False)
    telefone = lead_data.get("telefone")

    t = PROFILE_THRESHOLDS

    # Rule 1: DISQUALIFIED
    if rating and rating < t["disqualified_min_rating"]:
        return LeadProfile.DISQUALIFIED
    if review_count < t["disqualified_min_reviews_without_phone"] and not telefone:
        return LeadProfile.DISQUALIFIED
    if not (lead_data.get("nome") or telefone or lead_data.get("endereco")):
        return LeadProfile.DISQUALIFIED

    # Rule 2: HOT_NO_SITE
    if (not has_website
            and rating >= t["hot_no_site_min_rating"]
            and review_count >= t["hot_no_site_min_reviews"]):
        return LeadProfile.HOT_NO_SITE

    # Rule 3: HOT_BAD_SITE
    if (has_website
            and score >= t["hot_bad_site_min_score"]
            and (has_instagram or review_count >= t["hot_bad_site_min_reviews_when_no_instagram"])):
        return LeadProfile.HOT_BAD_SITE

    # Rule 4: COLD
    if (has_website
            and score < t["cold_max_score"]
            and has_ssl and has_analytics
            and (has_chatbot or has_whatsapp_cta)):
        return LeadProfile.COLD

    # Rule 5: WARM (catch-all)
    return LeadProfile.WARM


def classify(lead_data: dict, *, llm_client=None) -> ClassificationResult:
    """Main entry point: classify a lead by profile and nicho.

    Contract:
      - Never raises.
      - Always returns a ClassificationResult.
      - On any failure path, returns a fallback with error_reason populated.
    """
    # Guard against non-dict input
    if not isinstance(lead_data, dict):
        lead_data = {}

    try:
        profile = _classify_profile(lead_data)
    except Exception as exc:
        logger.exception("profile classification crashed: %s", exc)
        profile = LeadProfile.DISQUALIFIED

    # Nicho: fuzzy first, LLM fallback comes in next task (stub for now)
    try:
        nicho, source, confidence = _classify_nicho(lead_data, llm_client=llm_client)
        error_reason = None
    except Exception as exc:
        logger.exception("nicho classification crashed: %s", exc)
        nicho = NichoCanonico.OUTROS
        source = NichoSource.FAILED
        confidence = 0.0
        error_reason = str(exc)[:200]

    pacote, prioridade = PROFILE_TO_DERIVED[profile]

    return ClassificationResult(
        perfil_lead=profile,
        nicho_canonico=nicho,
        nicho_source=source,
        nicho_confidence=confidence,
        pacote_sugerido=pacote,
        prioridade=prioridade,
        classification_hash=_compute_hash(lead_data),
        error_reason=error_reason,
    )


def _classify_nicho(
    lead_data: dict, *, llm_client=None,
) -> tuple[NichoCanonico, NichoSource, float]:
    """3-layer nicho inference. LLM layer wired in Task 6.

    This stub covers layers 1 and 2 only; layer 3 returns OUTROS/failed.
    """
    raw = lead_data.get("nicho_raw") or ""

    # Layer 1+2: fuzzy match (implements exact substring at confidence=1.0)
    match = fuzzy_match_nicho(raw)
    if match is not None:
        bucket, conf = match
        if conf >= 0.999:
            return (bucket, NichoSource.APIFY_CATEGORY, 1.0)
        return (bucket, NichoSource.FUZZY_MATCH, conf)

    # Layer 3: LLM (stub — implemented in Task 6)
    if llm_client is not None:
        # placeholder: real LLM path added next task
        pass

    return (NichoCanonico.OUTROS, NichoSource.FAILED, 0.0)
```

- [ ] **Step 4: Rodar testes de perfil**

Run: `cd backend && pytest tests/test_classifier.py -v`
Expected: todos os tests passam (property-based pode demorar ~5s)

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/enrichment/classifier.py backend/tests/test_classifier.py
git commit -m "feat(classification): profile rules + nicho fuzzy matching (llm stub)"
```

---

### Task 6: Integrar LLM fallback pra nicho + retry

**Files:**
- Modify: `backend/app/pipeline/enrichment/classifier.py:_classify_nicho`
- Modify: `backend/tests/test_classifier.py`

- [ ] **Step 1: Adicionar testes com mock LLM**

Append em `backend/tests/test_classifier.py`:

```python
from unittest.mock import MagicMock


class _FakeToolUse:
    """Mimics anthropic.types.ToolUseBlock."""
    def __init__(self, input_dict):
        self.type = "tool_use"
        self.name = "classify_nicho"
        self.input = input_dict


class _FakeResponse:
    def __init__(self, content_blocks):
        self.content = content_blocks


def _make_llm(nicho_val, confidence=0.9):
    """Return a mock anthropic client that responds with a tool_use block."""
    client = MagicMock()
    client.messages.create.return_value = _FakeResponse([
        _FakeToolUse({
            "nicho_canonico": nicho_val,
            "confidence": confidence,
            "reasoning": "mock",
        })
    ])
    return client


def test_nicho_llm_fallback_used_when_fuzzy_fails():
    llm = _make_llm("advocacia", 0.92)
    result = classify(
        _base_lead(nicho_raw="Consultoria jurídica especializada"),
        llm_client=llm,
    )
    assert result.nicho_canonico == NichoCanonico.ADVOCACIA
    assert result.nicho_source == NichoSource.LLM_INFERRED
    assert result.nicho_confidence == 0.92


def test_nicho_llm_invalid_enum_value_falls_back_to_outros():
    llm = _make_llm("banco")  # not a valid bucket
    result = classify(
        _base_lead(nicho_raw="Agência bancária"),
        llm_client=llm,
    )
    assert result.nicho_canonico == NichoCanonico.OUTROS
    assert result.nicho_source == NichoSource.FAILED


def test_nicho_llm_exception_falls_back():
    llm = MagicMock()
    llm.messages.create.side_effect = Exception("boom")
    result = classify(
        _base_lead(nicho_raw="Negocio desconhecido xpto"),
        llm_client=llm,
    )
    assert result.nicho_canonico == NichoCanonico.OUTROS
    assert result.nicho_source == NichoSource.FAILED


def test_nicho_llm_not_called_when_fuzzy_matches():
    llm = _make_llm("academia")  # this should NOT be invoked
    result = classify(
        _base_lead(nicho_raw="Clínica Odontológica Dr Silva"),
        llm_client=llm,
    )
    # Fuzzy hits dentista directly; LLM is skipped
    assert result.nicho_canonico == NichoCanonico.DENTISTA
    llm.messages.create.assert_not_called()


def test_nicho_llm_low_confidence_kept_as_llm_inferred():
    llm = _make_llm("industria", 0.3)
    result = classify(
        _base_lead(nicho_raw="Fornecedor de peças automotivas B2B"),
        llm_client=llm,
    )
    # Source stays as LLM_INFERRED; review table picks it up via confidence<0.5
    assert result.nicho_source == NichoSource.LLM_INFERRED
    assert result.nicho_confidence == 0.3
```

- [ ] **Step 2: Rodar (fail)**

Run: `cd backend && pytest tests/test_classifier.py -v -k nicho_llm`
Expected: FAIL (LLM path ainda é stub)

- [ ] **Step 3: Implementar LLM fallback com retry**

Substituir a função `_classify_nicho` em `backend/app/pipeline/enrichment/classifier.py` pela versão completa:

```python
from tenacity import (
    Retrying, stop_after_attempt, wait_exponential_jitter,
    retry_if_exception_type, RetryError,
)

from app.pipeline.enrichment.classifier_prompts import (
    build_nicho_prompt, NICHO_TOOL_SCHEMA,
)


_VALID_NICHOS = {n.value for n in NichoCanonico}


def _call_llm_for_nicho(llm_client, lead_data: dict) -> tuple[NichoCanonico, float]:
    """Single LLM call with retry on transient failures.

    Returns (bucket, confidence). Raises on hard failure after retries.
    """
    prompt = build_nicho_prompt(
        nome=lead_data.get("nome") or "",
        nicho_raw=lead_data.get("nicho_raw") or "",
        descricao=lead_data.get("descricao") or "",
        reviews=lead_data.get("reviews") or [],
    )

    retryer = Retrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=8),
        retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)),
        reraise=True,
    )

    last_response = None
    for attempt in retryer:
        with attempt:
            last_response = llm_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                tools=[NICHO_TOOL_SCHEMA],
                tool_choice={"type": "tool", "name": "classify_nicho"},
                messages=[{"role": "user", "content": prompt}],
                timeout=15,
            )

    # Parse response
    tool_blocks = [b for b in last_response.content if getattr(b, "type", None) == "tool_use"]
    if not tool_blocks:
        raise ValueError("no tool_use block in response")

    data = tool_blocks[0].input or {}
    nicho_raw = data.get("nicho_canonico")
    if nicho_raw not in _VALID_NICHOS:
        raise ValueError(f"invalid enum value: {nicho_raw!r}")

    confidence = data.get("confidence", 0.5)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    return (NichoCanonico(nicho_raw), confidence)


def _classify_nicho(
    lead_data: dict, *, llm_client=None,
) -> tuple[NichoCanonico, NichoSource, float]:
    """3-layer nicho inference."""
    raw = lead_data.get("nicho_raw") or ""

    # Layers 1 + 2: fuzzy match (exact substring = 1.0, fuzzy ratio >= 0.75)
    match = fuzzy_match_nicho(raw)
    if match is not None:
        bucket, conf = match
        if conf >= 0.999:
            return (bucket, NichoSource.APIFY_CATEGORY, 1.0)
        return (bucket, NichoSource.FUZZY_MATCH, conf)

    # Layer 3: LLM
    if llm_client is None:
        return (NichoCanonico.OUTROS, NichoSource.FAILED, 0.0)

    try:
        bucket, conf = _call_llm_for_nicho(llm_client, lead_data)
        return (bucket, NichoSource.LLM_INFERRED, conf)
    except Exception as exc:
        logger.warning("LLM nicho classification failed: %s", exc)
        return (NichoCanonico.OUTROS, NichoSource.FAILED, 0.0)
```

- [ ] **Step 4: Rodar testes**

Run: `cd backend && pytest tests/test_classifier.py -v`
Expected: todos os tests passam (perfil + LLM fallback)

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/enrichment/classifier.py backend/tests/test_classifier.py
git commit -m "feat(classification): LLM fallback for nicho with retry and fallbacks"
```

---

### Task 7: Migration Alembic — 9 campos novos no Lead

**Files:**
- Create: `backend/alembic/versions/k04_lead_classification.py`
- Modify: `backend/app/models.py`

- [ ] **Step 1: Gerar migration autogenerada (base)**

```bash
cd backend && alembic revision -m "add lead classification fields"
```

Isso cria `backend/alembic/versions/<hash>_add_lead_classification_fields.py`. Renomear manualmente pra `k04_lead_classification.py` (mantendo o hash interno).

- [ ] **Step 2: Escrever `upgrade()` e `downgrade()`**

Conteúdo completo do `backend/alembic/versions/k04_lead_classification.py`:

```python
"""add lead classification fields

Revision ID: k04_classification
Revises: j03_dimensional_scoring
Create Date: 2026-04-20 00:00:00
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "k04_classification"
down_revision = "j03_dimensional_scoring"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("perfil_lead", sa.String(length=30), nullable=True))
    op.add_column("leads", sa.Column("nicho_canonico", sa.String(length=30), nullable=True))
    op.add_column("leads", sa.Column("nicho_source", sa.String(length=30), nullable=True))
    op.add_column("leads", sa.Column("nicho_confidence", sa.Float(), nullable=True))
    op.add_column("leads", sa.Column("pacote_sugerido", sa.String(length=30), nullable=True))
    op.add_column("leads", sa.Column("prioridade", sa.String(length=20), nullable=True))
    op.add_column("leads", sa.Column("classification_hash", sa.String(length=32), nullable=True))
    op.add_column("leads", sa.Column("classified_at", sa.DateTime(), nullable=True))
    op.add_column("leads", sa.Column("has_instagram", sa.Boolean(), nullable=True))

    op.create_index("idx_leads_perfil_lead", "leads", ["perfil_lead"])
    op.create_index("idx_leads_nicho_canonico", "leads", ["nicho_canonico"])
    op.create_index("idx_leads_pacote_sugerido", "leads", ["pacote_sugerido"])
    op.create_index("idx_leads_prioridade", "leads", ["prioridade"])


def downgrade() -> None:
    op.drop_index("idx_leads_prioridade", table_name="leads")
    op.drop_index("idx_leads_pacote_sugerido", table_name="leads")
    op.drop_index("idx_leads_nicho_canonico", table_name="leads")
    op.drop_index("idx_leads_perfil_lead", table_name="leads")
    op.drop_column("leads", "has_instagram")
    op.drop_column("leads", "classified_at")
    op.drop_column("leads", "classification_hash")
    op.drop_column("leads", "prioridade")
    op.drop_column("leads", "pacote_sugerido")
    op.drop_column("leads", "nicho_confidence")
    op.drop_column("leads", "nicho_source")
    op.drop_column("leads", "nicho_canonico")
    op.drop_column("leads", "perfil_lead")
```

Nota: usei `String(30)` em vez de `Enum` para evitar dor no Alembic em Postgres (enums nativos requerem DROP TYPE no downgrade, e aliás mudanças futuras nos enums ficam complicadas). O código Python usa os `str Enums` pra validar antes de persistir.

- [ ] **Step 3: Atualizar `backend/app/models.py` — classe `Lead`**

Editar `backend/app/models.py`. Adicionar os campos imediatamente antes da linha `lp_html = Column(Text)`:

```python
    # Classification fields (see classifier.py)
    perfil_lead = Column(String(30), nullable=True)
    nicho_canonico = Column(String(30), nullable=True)
    nicho_source = Column(String(30), nullable=True)
    nicho_confidence = Column(sa.Float, nullable=True)  # use sa.Float if imported, else Numeric
    pacote_sugerido = Column(String(30), nullable=True)
    prioridade = Column(String(20), nullable=True)
    classification_hash = Column(String(32), nullable=True)
    classified_at = Column(DateTime, nullable=True)
    has_instagram = Column(Boolean, nullable=True)
```

Importante: o import de `Float` já existe? Olhar a linha de imports (linha 5-8) e garantir `Float` importado — hoje tem `Numeric`, adicionar `Float`:

```python
from sqlalchemy import (
    Boolean, Column, Integer, String, Text, Numeric, Float,
    DateTime, Date, ForeignKey, Index, JSON, UniqueConstraint, func
)
```

Adicionar também novos índices na tupla `__table_args__`:

```python
    __table_args__ = (
        Index("idx_leads_status", "status"),
        Index("idx_leads_nicho", "nicho"),
        Index("idx_leads_cidade", "cidade"),
        Index("idx_leads_score", "opportunity_score"),
        Index("idx_leads_email", "email"),
        Index("idx_leads_cnpj", "cnpj"),
        Index("idx_leads_perfil_lead", "perfil_lead"),
        Index("idx_leads_nicho_canonico", "nicho_canonico"),
        Index("idx_leads_pacote_sugerido", "pacote_sugerido"),
        Index("idx_leads_prioridade", "prioridade"),
    )
```

- [ ] **Step 4: Rodar migration**

```bash
cd backend && alembic upgrade head
```

Expected: `Running upgrade j03_dimensional_scoring -> k04_classification, add lead classification fields`

- [ ] **Step 5: Rodar suíte de tests completa — nada deve quebrar**

Run: `cd backend && pytest`
Expected: todos os testes anteriores continuam passando + novos testes de classificação passando.

- [ ] **Step 6: Commit**

```bash
git add backend/alembic/versions/k04_lead_classification.py backend/app/models.py
git commit -m "feat(classification): migration and model fields for lead profile + nicho"
```

---

## Fase 2 — Backend integration (provider + orchestrator + scraper)

### Task 8: Criar `ClassificationProvider`

**Files:**
- Create: `backend/app/pipeline/enrichment/providers/classification_provider.py`
- Test: `backend/tests/test_classification_provider.py`

- [ ] **Step 1: Escrever teste**

Criar `backend/tests/test_classification_provider.py`:

```python
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.models import Lead
from app.pipeline.enrichment.base_provider import EnrichmentContext, ProviderResult
from app.pipeline.enrichment.providers.classification_provider import (
    ClassificationProvider,
)


def _lead(**kw):
    return Lead(
        nome=kw.get("nome", "Lead X"),
        rating=kw.get("rating", 4.5),
        reviews_count=kw.get("reviews_count", 50),
        website=kw.get("website", None),
        opportunity_score=kw.get("opportunity_score", 40),
        site_analysis=kw.get("site_analysis") or {},
        nicho=kw.get("nicho", "Clinica Odontologica"),
        has_instagram=kw.get("has_instagram", False),
        telefone="11999999999",
    )


def test_can_run_returns_true_always():
    provider = ClassificationProvider()
    assert provider.can_run(_lead()) is True
    assert provider.can_run(_lead(rating=None, reviews_count=None)) is True


def test_run_returns_provider_result():
    provider = ClassificationProvider(llm_client=None)
    result = provider.run(_lead(), EnrichmentContext())
    assert isinstance(result, ProviderResult)
    assert result.success is True
    assert result.source == "classification"
    assert "perfil_lead" in result.data
    assert "nicho_canonico" in result.data


def test_run_returns_hot_no_site_when_appropriate():
    lead = _lead(
        website=None, rating=4.7, reviews_count=80, nicho="Dentist",
    )
    provider = ClassificationProvider()
    result = provider.run(lead, EnrichmentContext())
    assert result.data["perfil_lead"] == "hot_no_site"
    assert result.data["nicho_canonico"] == "dentista"


def test_run_consolidates_site_analysis_flags():
    lead = _lead(
        website="https://foo.com",
        opportunity_score=10,
        site_analysis={
            "has_ssl": True, "has_analytics": True, "has_whatsapp_cta": True,
        },
    )
    provider = ClassificationProvider()
    result = provider.run(lead, EnrichmentContext())
    assert result.data["perfil_lead"] == "cold"


def test_run_never_raises():
    provider = ClassificationProvider()
    # Lead com campos esdrúxulos
    lead = Lead(nome=None, telefone=None)
    result = provider.run(lead, EnrichmentContext())
    assert isinstance(result, ProviderResult)
    # Falha graciosa → fallback
    assert result.success is True  # result ainda é válido, só com DISQUALIFIED
```

- [ ] **Step 2: Rodar (fail)**

Run: `cd backend && pytest tests/test_classification_provider.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Implementar provider**

Criar `backend/app/pipeline/enrichment/providers/classification_provider.py`:

```python
"""Classification provider — consumes data from all earlier providers."""
from __future__ import annotations

import logging
from typing import Any

from app.pipeline.enrichment.base_provider import (
    BaseProvider, EnrichmentContext, ProviderResult,
)
from app.pipeline.enrichment.classifier import classify

logger = logging.getLogger(__name__)


class ClassificationProvider(BaseProvider):
    name = "classification"
    display_name = "Lead Profile & Nicho Classification"
    required_fields: list[str] = []
    cost = "free"  # LLM is freemium-ish; minimal cost per lead

    def __init__(self, llm_client: Any = None):
        self._llm_client = llm_client

    def can_run(self, lead, context: EnrichmentContext | None = None) -> bool:
        return True  # classifier é tolerante a dados faltando

    def run(self, lead, context: EnrichmentContext) -> ProviderResult:
        try:
            lead_data = self._consolidate(lead)
            result = classify(lead_data, llm_client=self._llm_client)
            return ProviderResult(
                success=True,
                data=result.to_dict(),
                errors=[result.error_reason] if result.error_reason else [],
                source=self.name,
            )
        except Exception as exc:
            logger.exception("classification provider crashed: %s", exc)
            return ProviderResult(
                success=False,
                data={},
                errors=[f"unexpected: {str(exc)[:200]}"],
                source=self.name,
            )

    def _consolidate(self, lead) -> dict:
        """Build the dict passed to classify()."""
        sa = getattr(lead, "site_analysis", None) or {}
        top_reviews = getattr(lead, "top_reviews", None) or []
        reviews_text = []
        for r in top_reviews[:3]:
            if isinstance(r, dict):
                reviews_text.append(r.get("text") or r.get("comment") or "")
            elif isinstance(r, str):
                reviews_text.append(r)

        rating = getattr(lead, "rating", None)
        return {
            "has_website": bool(getattr(lead, "website", None)),
            "score": getattr(lead, "opportunity_score", None),
            "rating": float(rating) if rating is not None else None,
            "review_count": getattr(lead, "reviews_count", None),
            "has_ssl": sa.get("has_ssl"),
            "has_analytics": sa.get("has_analytics"),
            "has_chatbot": sa.get("has_chatbot"),
            "has_whatsapp_cta": sa.get("has_whatsapp_cta"),
            "has_instagram": getattr(lead, "has_instagram", None),
            "nicho_raw": getattr(lead, "nicho", None) or getattr(lead, "categoria", None),
            "nome": getattr(lead, "nome", None),
            "descricao": sa.get("description") or "",
            "reviews": [r for r in reviews_text if r],
            "telefone": getattr(lead, "telefone", None),
            "endereco": getattr(lead, "endereco", None),
        }
```

- [ ] **Step 4: Rodar testes**

Run: `cd backend && pytest tests/test_classification_provider.py -v`
Expected: 5 tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/enrichment/providers/classification_provider.py backend/tests/test_classification_provider.py
git commit -m "feat(classification): add ClassificationProvider wrapping pure classify()"
```

---

### Task 9: Integrar provider no orchestrator

**Files:**
- Modify: `backend/app/pipeline/enrichment/orchestrator.py`
- Test: adicionar em `backend/tests/test_classification_provider.py`

- [ ] **Step 1: Adicionar teste de integração orchestrator**

Append em `backend/tests/test_classification_provider.py`:

```python
from app.pipeline.enrichment.orchestrator import EnrichmentOrchestrator
from app.pipeline.enrichment.providers.classification_provider import (
    ClassificationProvider,
)


def test_orchestrator_includes_classification_in_phase_order():
    orch = EnrichmentOrchestrator()
    assert "classification" in orch._providers_by_name


def test_orchestrator_always_runs_classification():
    # Lead sem website não ativa crawl chain; classification deve rodar mesmo assim
    from app.models import Lead
    lead = Lead(nome="X", telefone="11", rating=4.0, reviews_count=10)
    orch = EnrichmentOrchestrator()
    plan = orch.plan(lead, skip_providers=["cnpj_enricher"])
    names = [p.name for p in plan.providers]
    assert "classification" in names
    assert names.index("classification") == len(names) - 1  # sempre última


def test_orchestrator_execute_writes_classification_fields():
    from app.models import Lead
    lead = Lead(
        nome="X", telefone="11999", rating=4.5, reviews_count=60,
        nicho="Pizzaria",
    )
    orch = EnrichmentOrchestrator()
    plan = orch.plan(lead, skip_providers=[
        "cnpj_enricher", "website_crawler", "schema_extractor",
        "tech_stack", "email_discoverer", "apollo",
    ])
    out = orch.execute(lead, plan)
    assert "perfil_lead" in out
    assert out["perfil_lead"] == "hot_no_site"
    assert out["nicho_canonico"] == "restaurante"
```

- [ ] **Step 2: Rodar (fail — ainda não está no phase order)**

Run: `cd backend && pytest tests/test_classification_provider.py -v -k orchestrator`
Expected: FAIL

- [ ] **Step 3: Modificar orchestrator**

Editar `backend/app/pipeline/enrichment/orchestrator.py`:

1. Adicionar import:

```python
from app.pipeline.enrichment.providers.classification_provider import (
    ClassificationProvider,
)
```

2. Adicionar ao `_default_providers()`:

```python
def _default_providers() -> list[BaseProvider]:
    return [
        CnpjProvider(),
        WebsiteCrawlerProvider(),
        SchemaOrgProvider(),
        TechStackProvider(),
        EmailDiscovererProvider(),
        ApolloProvider(),
        ClassificationProvider(),
    ]
```

3. Adicionar ao `_PHASE_ORDER`:

```python
_PHASE_ORDER = [
    "cnpj_enricher",
    "website_crawler",
    "schema_extractor",
    "tech_stack",
    "email_discoverer",
    "apollo",
    "classification",
]
```

4. Em `plan()`, adicionar `"classification"` ao `optimistic_names` sempre (não depende de crawl chain):

Localizar:

```python
        optimistic_names = (
            {
                "website_crawler",
                ...
            }
            if include_crawl_chain
            else set()
        )
```

Substituir por:

```python
        optimistic_names = (
            {
                "website_crawler",
                "schema_extractor",
                "tech_stack",
                "email_discoverer",
                "apollo",
            }
            if include_crawl_chain
            else set()
        )
        optimistic_names.add("classification")  # classificação sempre roda
```

5. Em `execute()`, tratar os 9 novos campos. Eles vêm em `result.data` como chaves flat. Adicionar ao final de `execute()` (antes de `return`):

Localizar o `return { ... }` no final do método. Adicionar ao dicionário de retorno captura dos campos classificação:

```python
        # --- Classification (coming from ClassificationProvider.run) ---
        classification_fields = {}
        for provider in plan.providers:
            if provider.name == "classification":
                # Já foi executado no loop acima; recuperar do último enrichment_sources?
                # Melhor: re-run só o classifier aqui se precisar. Mas o loop principal
                # já retornou o result e perdeu a referência. Solução: o loop principal
                # deve bufferizar o result.data do classifier antes do merge.
                pass
```

Isso é complexo. Melhor: modificar o **loop principal** do `execute()` pra bufferizar o result do classification provider. Localizar dentro do loop `for provider in plan.providers:` e logo após `data = result.data or {}`:

```python
                data = result.data or {}

                # Capture classification-specific fields
                if provider.name == "classification":
                    for k in (
                        "perfil_lead", "nicho_canonico", "nicho_source",
                        "nicho_confidence", "pacote_sugerido", "prioridade",
                        "classification_hash",
                    ):
                        if k in data:
                            flat[k] = data[k]
```

Adicionar `"classified_at"` também — setado automaticamente pelo caller após o orchestrator retornar.

- [ ] **Step 4: Rodar testes**

Run: `cd backend && pytest tests/test_classification_provider.py -v`
Expected: todos passam (incluindo os de orchestrator)

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/enrichment/orchestrator.py backend/tests/test_classification_provider.py
git commit -m "feat(classification): integrate ClassificationProvider into orchestrator"
```

---

### Task 10: Persistência pelo `enricher.py` + `classified_at`

**Files:**
- Modify: `backend/app/pipeline/enricher.py`
- Test: adicionar em `backend/tests/test_classification_provider.py`

- [ ] **Step 1: Adicionar teste**

Append em `backend/tests/test_classification_provider.py`:

```python
from datetime import datetime

from app.pipeline.enricher import enrich_lead_via_orchestrator


def test_enricher_persists_classification_fields(db_session):
    """Smoke test: full pipeline writes perfil_lead et al. to the Lead row."""
    from app.models import Lead
    lead = Lead(
        nome="Pizzaria Bella",
        telefone="11999999999",
        rating=4.5,
        reviews_count=60,
        nicho="Pizzaria",
    )
    db_session.add(lead)
    db_session.commit()

    enrich_lead_via_orchestrator(
        db_session, lead,
        skip_providers=[
            "cnpj_enricher", "website_crawler", "schema_extractor",
            "tech_stack", "email_discoverer", "apollo",
        ],
    )
    db_session.refresh(lead)
    assert lead.perfil_lead == "hot_no_site"
    assert lead.nicho_canonico == "restaurante"
    assert lead.pacote_sugerido is not None
    assert lead.prioridade is not None
    assert lead.classification_hash is not None
    assert lead.classified_at is not None
```

Usa fixture `db_session` já existente em `backend/tests/conftest.py`.

- [ ] **Step 2: Rodar (fail)**

Run: `cd backend && pytest tests/test_classification_provider.py::test_enricher_persists_classification_fields -v`
Expected: FAIL — campos ficam NULL após enrich

- [ ] **Step 3: Modificar `enricher.py` pra persistir os campos**

Abrir `backend/app/pipeline/enricher.py` e localizar a função `enrich_lead_via_orchestrator()`. Encontrar o bloco que aplica `out` ao `lead` (o dict retornado pelo orchestrator). Adicionar **antes do commit**:

```python
    # --- Classification fields (from ClassificationProvider) ---
    for attr in (
        "perfil_lead", "nicho_canonico", "nicho_source",
        "nicho_confidence", "pacote_sugerido", "prioridade",
        "classification_hash",
    ):
        if attr in out and out[attr] is not None:
            setattr(lead, attr, out[attr])

    if "perfil_lead" in out:
        from datetime import datetime
        lead.classified_at = datetime.utcnow()
```

Nota: ajustar o local exato depende de como `enricher.py` está hoje. Se tiver dúvida sobre onde inserir, procurar por `lead.opportunity_score = out[` ou similar — é o mesmo padrão.

- [ ] **Step 4: Rodar teste**

Run: `cd backend && pytest tests/test_classification_provider.py::test_enricher_persists_classification_fields -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/enricher.py backend/tests/test_classification_provider.py
git commit -m "feat(classification): persist classification fields via enricher"
```

---

### Task 11: Capturar `has_instagram` no scraper

**Files:**
- Modify: `backend/app/pipeline/scraper.py`
- Modify: `backend/app/routers/pipeline.py` (onde Lead é instanciado a partir do scrape)
- Test: `backend/tests/test_scraper_instagram.py` (novo)

- [ ] **Step 1: Escrever teste**

Criar `backend/tests/test_scraper_instagram.py`:

```python
from app.pipeline.scraper import extract_has_instagram


def test_extract_has_instagram_from_url_field():
    payload = {"website": "https://restaurante.com", "instagramUrl": "https://instagram.com/abc"}
    assert extract_has_instagram(payload) is True


def test_extract_has_instagram_from_social_links():
    payload = {"socialLinks": [{"service": "Instagram", "url": "https://ig.com/x"}]}
    assert extract_has_instagram(payload) is True


def test_extract_has_instagram_returns_false_when_absent():
    payload = {"website": "https://foo.com"}
    assert extract_has_instagram(payload) is False


def test_extract_has_instagram_handles_none():
    assert extract_has_instagram({}) is False
    assert extract_has_instagram(None) is False
```

- [ ] **Step 2: Rodar (fail)**

Run: `cd backend && pytest tests/test_scraper_instagram.py -v`
Expected: FAIL `ImportError`

- [ ] **Step 3: Implementar helper em `scraper.py`**

Abrir `backend/app/pipeline/scraper.py` e adicionar no topo (após imports):

```python
def extract_has_instagram(payload: dict | None) -> bool:
    """Check if Apify Google Maps payload indicates Instagram presence.

    Checks common fields: 'instagramUrl', 'socialLinks', bio text. Never raises.
    """
    if not payload or not isinstance(payload, dict):
        return False

    # Direct field
    if payload.get("instagramUrl"):
        return True

    # socialLinks array (compass actor format)
    social = payload.get("socialLinks") or []
    if isinstance(social, list):
        for entry in social:
            if not isinstance(entry, dict):
                continue
            service = (entry.get("service") or entry.get("platform") or "").lower()
            url = (entry.get("url") or "").lower()
            if "instagram" in service or "instagram.com" in url:
                return True

    # Inline instagram link in website or description fields
    for key in ("website", "websiteUri", "url", "description"):
        v = payload.get(key)
        if isinstance(v, str) and "instagram.com" in v.lower():
            return True

    return False
```

- [ ] **Step 4: Rodar teste**

Run: `cd backend && pytest tests/test_scraper_instagram.py -v`
Expected: 4 tests pass

- [ ] **Step 5: Popular `has_instagram` ao criar Lead**

Em `backend/app/pipeline/scraper.py`, localizar onde o dict do lead é montado (função `scrape_all` ou equivalente). Adicionar chave `"has_instagram"`:

```python
    lead_dict = {
        # ... campos existentes ...
        "has_instagram": extract_has_instagram(raw_payload),
    }
```

Em `backend/app/routers/pipeline.py`, função `_run_scrape` (linhas ~61-82), adicionar ao `Lead(...)`:

```python
                lead = Lead(
                    # ... campos existentes ...
                    has_instagram=ld.get("has_instagram"),
                    # ...
                )
```

- [ ] **Step 6: Rodar suíte inteira**

Run: `cd backend && pytest`
Expected: tudo passa

- [ ] **Step 7: Commit**

```bash
git add backend/app/pipeline/scraper.py backend/app/routers/pipeline.py backend/tests/test_scraper_instagram.py
git commit -m "feat(scraper): capture has_instagram from Apify payload"
```

---

## Fase 3 — Backend APIs (endpoints + batch job)

### Task 12: Endpoint reclassify individual

**Files:**
- Modify: `backend/app/routers/leads.py`
- Modify: `backend/app/schemas.py`
- Test: `backend/tests/test_reclassify_api.py`

- [ ] **Step 1: Adicionar schemas em `backend/app/schemas.py`**

Append:

```python
from pydantic import BaseModel


class ReclassifyRequest(BaseModel):
    force: bool = True


class ClassifyRequest(BaseModel):
    scope: str = "unclassified"  # unclassified | all | by_job | by_status
    scope_filter: dict | None = None
    force: bool = False
```

- [ ] **Step 2: Escrever teste**

Criar `backend/tests/test_reclassify_api.py`:

```python
def test_reclassify_single_lead(client, sample_lead):
    resp = client.post(f"/api/leads/{sample_lead.id}/reclassify")
    assert resp.status_code == 200
    body = resp.json()
    assert body["perfil_lead"] is not None
    assert body["nicho_canonico"] is not None


def test_reclassify_404_on_missing(client):
    resp = client.post("/api/leads/999999/reclassify")
    assert resp.status_code == 404


def test_reclassify_marks_manual_source_for_specific_field_update(client, sample_lead):
    resp = client.patch(
        f"/api/leads/{sample_lead.id}",
        json={"nicho_canonico": "dentista"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["nicho_canonico"] == "dentista"
    assert body["nicho_source"] == "manual"
```

- [ ] **Step 3: Rodar (fail)**

Run: `cd backend && pytest tests/test_reclassify_api.py -v`
Expected: FAIL

- [ ] **Step 4: Implementar endpoint em `backend/app/routers/leads.py`**

Adicionar import no topo:

```python
from app.pipeline.enrichment.classifier import classify
```

Adicionar endpoint:

```python
@router.post("/{lead_id}/reclassify", response_model=LeadOut)
def reclassify_lead(
    lead_id: int, body: ReclassifyRequest | None = None,
    db: Session = Depends(get_db),
):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Lock (best-effort; SQLite in tests ignores)
    try:
        db.query(Lead).filter(Lead.id == lead_id).with_for_update(nowait=False).first()
    except Exception:
        pass

    from app.pipeline.enrichment.providers.classification_provider import (
        ClassificationProvider,
    )
    provider = ClassificationProvider()
    lead_data = provider._consolidate(lead)
    result = classify(lead_data)

    for k, v in result.to_dict().items():
        if hasattr(lead, k):
            setattr(lead, k, v)
    from datetime import datetime
    lead.classified_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)
    return lead
```

- [ ] **Step 5: Modificar PATCH /api/leads/{id} pra marcar source=manual**

Localizar o endpoint PATCH existente em `leads.py`. No handler, após aplicar os campos do body, adicionar:

```python
    if "nicho_canonico" in body_dict:
        lead.nicho_source = "manual"
        lead.nicho_confidence = 1.0
```

Substitua `body_dict` pelo nome real do dict do payload no código existente.

- [ ] **Step 6: Rodar testes**

Run: `cd backend && pytest tests/test_reclassify_api.py -v`
Expected: 3 tests pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/leads.py backend/app/schemas.py backend/tests/test_reclassify_api.py
git commit -m "feat(api): add reclassify endpoint and manual nicho override"
```

---

### Task 13: Batch classify endpoint + background job

**Files:**
- Modify: `backend/app/routers/pipeline.py`
- Test: `backend/tests/test_classify_job.py`

- [ ] **Step 1: Escrever teste**

Criar `backend/tests/test_classify_job.py`:

```python
from unittest.mock import patch

from app.models import Lead


def test_classify_job_endpoint_creates_job(client, db_session):
    # Setup: 3 leads sem perfil
    for i in range(3):
        db_session.add(Lead(
            nome=f"Lead {i}", telefone="11999", rating=4.5, reviews_count=50,
            nicho="Pizzaria",
        ))
    db_session.commit()

    resp = client.post("/api/pipeline/classify", json={"scope": "unclassified"})
    assert resp.status_code == 200
    body = resp.json()
    assert "job_id" in body


def test_classify_job_isolates_lead_failures(client, db_session):
    # Inject a bad lead that will fail consolidation
    db_session.add(Lead(nome=None, telefone=None))
    for i in range(3):
        db_session.add(Lead(
            nome=f"OK {i}", telefone="11", rating=4.5, reviews_count=50,
            nicho="Pizzaria",
        ))
    db_session.commit()

    with patch("app.routers.pipeline._run_classify_sync") as mocked:
        from app.routers.pipeline import _run_classify
        _run_classify(1, {"scope": "unclassified", "force": False})
        # Mock shouldn't matter; but the important thing is no raise
```

(Adaptar conforme estrutura real do conftest; testes mais robustos em tests/test_classification_resilience.py.)

- [ ] **Step 2: Rodar (fail)**

Run: `cd backend && pytest tests/test_classify_job.py -v`
Expected: FAIL

- [ ] **Step 3: Implementar endpoint + runner em `backend/app/routers/pipeline.py`**

Adicionar no topo os imports:

```python
from app.pipeline.enrichment.classifier import classify
from app.pipeline.enrichment.providers.classification_provider import (
    ClassificationProvider,
)
```

Adicionar função runner (similar ao `_run_scrape` e `_run_enrich`):

```python
def _run_classify(job_id: int, params: dict):
    """Background runner for batch classification.

    Isolates failures per-lead. Circuit breaker at 50% failure rate after 20 leads.
    """
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()
        _emit(job_id, {"type": "started", "job_id": job_id})

        scope = params.get("scope", "unclassified")
        scope_filter = params.get("scope_filter") or {}
        force = params.get("force", False)

        query = db.query(Lead)
        if scope == "unclassified":
            query = query.filter(Lead.perfil_lead.is_(None))
        elif scope == "by_job":
            jid = scope_filter.get("job_id")
            if jid:
                query = query.filter(Lead.job_id == jid)
        elif scope == "by_status":
            st = scope_filter.get("status")
            if st:
                query = query.filter(Lead.status == st)
        # "all" → no filter

        leads = query.all()
        total = len(leads)
        _emit(job_id, {"type": "progress", "current": 0, "total": total})

        results = {"ok": 0, "failed": 0, "skipped": 0, "errors": {}}
        provider = ClassificationProvider()

        for idx, lead in enumerate(leads):
            try:
                # Idempotency: compute new hash, skip if unchanged
                lead_data = provider._consolidate(lead)
                result = classify(lead_data)

                if (lead.classification_hash == result.classification_hash
                        and not force):
                    results["skipped"] += 1
                else:
                    # Preserve manual nicho
                    if lead.nicho_source == "manual" and not force:
                        result.nicho_canonico = lead.nicho_canonico
                        result.nicho_source = lead.nicho_source
                        result.nicho_confidence = lead.nicho_confidence

                    for k, v in result.to_dict().items():
                        if hasattr(lead, k):
                            setattr(lead, k, v)
                    lead.classified_at = datetime.utcnow()
                    db.commit()

                    if result.nicho_source == "failed":
                        results["failed"] += 1
                    else:
                        results["ok"] += 1
            except Exception as exc:
                db.rollback()
                results["failed"] += 1
                results["errors"][lead.id] = str(exc)[:200]

            # Circuit breaker
            if idx + 1 >= 20:
                failure_rate = results["failed"] / (idx + 1)
                if failure_rate > 0.5:
                    job.status = "stalled"
                    job.result_summary = {**results, "reason": "too_many_failures"}
                    job.finished_at = datetime.utcnow()
                    db.commit()
                    _emit(job_id, {"type": "error", "message": "too_many_failures"})
                    return

            # Progress every 5 leads
            if (idx + 1) % 5 == 0 or (idx + 1) == total:
                _emit(job_id, {
                    "type": "progress",
                    "current": idx + 1, "total": total,
                    "summary": results,
                })

        job.status = "done_with_errors" if results["failed"] else "done"
        job.result_summary = results
        job.finished_at = datetime.utcnow()
        db.commit()
        _emit(job_id, {"type": "done", "summary": results})

    except Exception as exc:
        db.rollback()
        job = db.get(Job, job_id)
        if job:
            job.status = "failed"
            job.error_message = str(exc)[:500]
            job.finished_at = datetime.utcnow()
            db.commit()
        _emit(job_id, {"type": "error", "message": str(exc)[:500]})
    finally:
        db.close()
```

Adicionar endpoint:

```python
@router.post("/pipeline/classify", response_model=JobOut)
def start_classify_job(
    body: ClassifyRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job = Job(type="classification", status="pending", params=body.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(_run_classify, job.id, body.model_dump())
    return job
```

Atualizar o `ClassifyRequest` import se necessário no topo do arquivo:

```python
from app.schemas import (
    ScrapeRequest, EnrichRequest, GenerateRequest, OutreachRequest,
    JobOut, JobListOut, PipelineStatusOut,
    ClassifyRequest,  # novo
)
```

- [ ] **Step 4: Rodar teste**

Run: `cd backend && pytest tests/test_classify_job.py -v`
Expected: testes passam

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/pipeline.py backend/tests/test_classify_job.py
git commit -m "feat(api): batch classification endpoint with SSE and circuit breaker"
```

---

### Task 14: Auto-dispatch após CSV import

**Files:**
- Modify: `backend/app/routers/pipeline.py` (no runner de csv-import)
- Test: `backend/tests/test_csv_import_chain.py`

- [ ] **Step 1: Escrever teste**

Criar `backend/tests/test_csv_import_chain.py`:

```python
import io


def test_csv_import_triggers_classification_job(client, db_session):
    csv_content = (
        "nome,telefone,rating,reviews_count,nicho\n"
        "Lead A,11999,4.5,50,Pizzaria\n"
        "Lead B,11888,4.7,80,Clinica Odontologica\n"
    )
    resp = client.post(
        "/api/pipeline/csv-import",
        files={"file": ("x.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        data={"nicho": "pizzaria", "cidade": "sp"},
    )
    assert resp.status_code == 200

    from app.models import Job
    jobs = db_session.query(Job).order_by(Job.id.desc()).limit(2).all()
    types = {j.type for j in jobs}
    assert "csv_import" in types
    assert "classification" in types
```

- [ ] **Step 2: Rodar (fail)**

Run: `cd backend && pytest tests/test_csv_import_chain.py -v`
Expected: FAIL

- [ ] **Step 3: Modificar `_run_csv_import`**

No `pipeline.py`, localizar função `_run_csv_import` (ou equivalente). Ao final do try (depois de `job.status = "done"`), antes do `_emit`/finally, adicionar:

```python
        # Chain: trigger classification over the imported batch
        try:
            classify_job = Job(
                type="classification", status="pending",
                params={
                    "scope": "by_job",
                    "scope_filter": {"job_id": job_id},
                    "force": False,
                },
            )
            db.add(classify_job)
            db.commit()
            # Run in same thread (we're already in a background task)
            import threading
            threading.Thread(
                target=_run_classify,
                args=(classify_job.id, classify_job.params),
                daemon=True,
            ).start()
        except Exception as exc:
            logger.warning("failed to chain classification: %s", exc)
```

(Se `logger` não estiver importado no arquivo, adicionar `import logging; logger = logging.getLogger(__name__)`.)

- [ ] **Step 4: Rodar teste**

Run: `cd backend && pytest tests/test_csv_import_chain.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/pipeline.py backend/tests/test_csv_import_chain.py
git commit -m "feat(api): auto-dispatch classification after CSV import"
```

---

### Task 15: Filtros de perfil/nicho em GET /api/leads + endpoint review

**Files:**
- Modify: `backend/app/routers/leads.py`
- Modify: `backend/app/schemas.py` (expor campos)
- Test: `backend/tests/test_leads_filters.py`

- [ ] **Step 1: Adicionar testes**

Criar `backend/tests/test_leads_filters.py`:

```python
from app.models import Lead


def test_filter_by_perfil_lead(client, db_session):
    db_session.add(Lead(nome="A", telefone="1", perfil_lead="hot_no_site"))
    db_session.add(Lead(nome="B", telefone="2", perfil_lead="warm"))
    db_session.commit()

    resp = client.get("/api/leads?perfil_lead=hot_no_site")
    assert resp.status_code == 200
    names = [l["nome"] for l in resp.json()["leads"]]
    assert names == ["A"]


def test_filter_by_nicho_canonico(client, db_session):
    db_session.add(Lead(nome="X", telefone="1", nicho_canonico="dentista"))
    db_session.add(Lead(nome="Y", telefone="2", nicho_canonico="restaurante"))
    db_session.commit()

    resp = client.get("/api/leads?nicho_canonico=dentista")
    assert resp.status_code == 200
    names = [l["nome"] for l in resp.json()["leads"]]
    assert names == ["X"]


def test_order_by_prioridade(client, db_session):
    db_session.add(Lead(nome="H", telefone="1", prioridade="maxima"))
    db_session.add(Lead(nome="W", telefone="2", prioridade="media"))
    db_session.add(Lead(nome="D", telefone="3", prioridade="pular"))
    db_session.commit()

    resp = client.get("/api/leads?order_by=prioridade")
    assert resp.status_code == 200
    names = [l["nome"] for l in resp.json()["leads"]]
    assert names == ["H", "W", "D"]


def test_review_endpoint_returns_problematic_leads(client, db_session):
    db_session.add(Lead(
        nome="In review", telefone="1",
        nicho_canonico="outros", nicho_source="failed",
    ))
    db_session.add(Lead(
        nome="OK", telefone="2",
        nicho_canonico="dentista", nicho_source="fuzzy_match",
        nicho_confidence=0.95,
    ))
    db_session.commit()

    resp = client.get("/api/leads/review")
    assert resp.status_code == 200
    names = [l["nome"] for l in resp.json()["leads"]]
    assert "In review" in names
    assert "OK" not in names
```

- [ ] **Step 2: Rodar (fail)**

Run: `cd backend && pytest tests/test_leads_filters.py -v`
Expected: FAIL

- [ ] **Step 3: Adicionar filtros no endpoint `GET /api/leads`**

Em `backend/app/routers/leads.py`, localizar o endpoint que lista leads. Adicionar query params:

```python
@router.get("", response_model=LeadListOut)
def list_leads(
    # ... params existentes ...
    perfil_lead: str | None = None,
    nicho_canonico: str | None = None,
    order_by: str | None = "score_desc",
    db: Session = Depends(get_db),
):
    query = db.query(Lead)
    # ... filtros existentes ...

    if perfil_lead:
        query = query.filter(Lead.perfil_lead == perfil_lead)
    if nicho_canonico:
        query = query.filter(Lead.nicho_canonico == nicho_canonico)

    if order_by == "prioridade":
        # Order by prioridade ranking (custom SQL CASE)
        from sqlalchemy import case
        prio_order = case(
            (Lead.prioridade == "maxima", 1),
            (Lead.prioridade == "alta", 2),
            (Lead.prioridade == "media", 3),
            (Lead.prioridade == "baixa", 4),
            (Lead.prioridade == "pular", 5),
            else_=6,
        )
        query = query.order_by(prio_order, Lead.opportunity_score.desc())
    # ... outros order_by existentes ...

    # ... resto do handler ...
```

- [ ] **Step 4: Adicionar endpoint review**

Ainda em `leads.py`:

```python
@router.get("/review", response_model=LeadListOut)
def list_leads_for_review(
    page: int = 1, per_page: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(Lead).filter(
        (Lead.nicho_canonico == "outros")
        | (Lead.nicho_source == "failed")
        | (Lead.nicho_confidence < 0.5)
    )
    total = query.count()
    offset = (page - 1) * per_page
    leads = query.offset(offset).limit(per_page).all()
    return {"leads": leads, "total": total, "page": page, "per_page": per_page}
```

- [ ] **Step 5: Expor campos novos nos schemas**

Em `backend/app/schemas.py`, localizar `LeadOut` e `LeadSummaryOut`. Adicionar campos:

```python
class LeadOut(BaseModel):
    # ... campos existentes ...
    perfil_lead: str | None = None
    nicho_canonico: str | None = None
    nicho_source: str | None = None
    nicho_confidence: float | None = None
    pacote_sugerido: str | None = None
    prioridade: str | None = None
    has_instagram: bool | None = None
    classified_at: datetime | None = None

    class Config:
        from_attributes = True


class LeadSummaryOut(BaseModel):
    # ... campos existentes ...
    perfil_lead: str | None = None
    nicho_canonico: str | None = None
    pacote_sugerido: str | None = None
    prioridade: str | None = None
    has_instagram: bool | None = None

    class Config:
        from_attributes = True
```

- [ ] **Step 6: Rodar testes**

Run: `cd backend && pytest tests/test_leads_filters.py -v`
Expected: 4 tests pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/leads.py backend/app/schemas.py backend/tests/test_leads_filters.py
git commit -m "feat(api): filters by perfil/nicho + /leads/review + order_by prioridade"
```

---

### Task 16: Testes E2E de resiliência

**Files:**
- Create: `backend/tests/test_classification_resilience.py`

- [ ] **Step 1: Escrever testes completos de resiliência**

Criar `backend/tests/test_classification_resilience.py`:

```python
"""End-to-end resilience tests for classification pipeline.

Validates spec section 7 guarantees:
- classify() never raises
- Circuit breaker fires at 50% failures after 20 leads
- Batch tolerates per-lead failures
- Idempotency via hash
"""
from unittest.mock import patch

import pytest

from app.models import Lead


def test_classify_never_raises_with_random_garbage():
    from app.pipeline.enrichment.classifier import classify
    garbage = [
        {},
        {"score": "banana"},
        {"rating": [1, 2, 3]},
        {"has_website": object()},
        {"review_count": -999},
        {"nome": None, "telefone": None, "rating": None},
    ]
    for g in garbage:
        result = classify(g)
        assert result is not None
        assert result.perfil_lead is not None


def test_batch_job_tolerates_individual_failures(client, db_session):
    # 30 leads; 10 deles com dados que quebrariam consolidação se não isolado
    for i in range(30):
        db_session.add(Lead(
            nome=f"Lead {i}" if i % 3 else None,
            telefone=f"11999{i}",
            rating=4.5 if i % 2 else None,
            reviews_count=50,
            nicho="Pizzaria" if i % 4 else "Clinica",
        ))
    db_session.commit()

    resp = client.post("/api/pipeline/classify", json={"scope": "unclassified"})
    assert resp.status_code == 200
    job_id = resp.json()["id"]

    # Wait for job (background task is sync in tests)
    from app.models import Job
    import time
    for _ in range(20):
        job = db_session.query(Job).filter(Job.id == job_id).first()
        db_session.refresh(job)
        if job.status in ("done", "done_with_errors", "failed", "stalled"):
            break
        time.sleep(0.2)
    assert job.status in ("done", "done_with_errors")
    assert job.result_summary["ok"] + job.result_summary["failed"] >= 25


def test_circuit_breaker_fires_on_high_failure_rate(db_session):
    from app.routers.pipeline import _run_classify

    # Adicionar 25 leads
    for i in range(25):
        db_session.add(Lead(nome=f"L{i}", telefone="11"))
    db_session.commit()

    from app.models import Job
    job = Job(type="classification", status="pending", params={})
    db_session.add(job)
    db_session.commit()
    job_id = job.id

    # Mock classify() to fail 100% of the time
    with patch(
        "app.routers.pipeline.classify",
        side_effect=Exception("boom"),
    ):
        _run_classify(job_id, {"scope": "unclassified"})

    db_session.refresh(job)
    assert job.status == "stalled"
    assert job.result_summary.get("reason") == "too_many_failures"


def test_idempotency_via_hash(client, db_session):
    db_session.add(Lead(
        nome="X", telefone="11", rating=4.5, reviews_count=50, nicho="Pizzaria",
    ))
    db_session.commit()

    # Run 1
    resp1 = client.post("/api/pipeline/classify", json={"scope": "unclassified"})
    assert resp1.status_code == 200

    # Run 2 (already classified → should skip all)
    resp2 = client.post("/api/pipeline/classify", json={"scope": "all"})
    assert resp2.status_code == 200

    from app.models import Job
    # Last job should have 1 skipped
    latest = db_session.query(Job).order_by(Job.id.desc()).first()
    # job depends on async — check result_summary when finished
```

(Ajustar pra async esperar job completar, seguindo padrão do conftest.)

- [ ] **Step 2: Rodar**

Run: `cd backend && pytest tests/test_classification_resilience.py -v`
Expected: todos passam

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_classification_resilience.py
git commit -m "test(classification): e2e resilience tests (circuit breaker, idempotency)"
```

---

## Fase 4 — Frontend

### Task 17: Atualizar types e API client

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Ler `types.ts` atual e adicionar campos**

Abrir `frontend/src/lib/types.ts`. Localizar o type `Lead`. Adicionar campos novos:

```typescript
export type LeadProfile =
  | "hot_no_site"
  | "hot_bad_site"
  | "warm"
  | "cold"
  | "disqualified";

export type NichoCanonico =
  | "dentista" | "estetica" | "salao_barbearia" | "restaurante"
  | "petshop_vet" | "academia" | "contabilidade" | "imobiliaria"
  | "loja_roupas" | "auto_escola" | "advocacia" | "industria"
  | "clinica_medica" | "escola_curso" | "outros";

export type NichoSource =
  | "apify_category" | "fuzzy_match" | "llm_inferred" | "manual" | "failed";

export type PacoteSugerido = "essencial" | "profissional" | "premium" | "skip";

export type Prioridade = "maxima" | "alta" | "media" | "baixa" | "pular";

// Extend existing Lead type:
export type Lead = {
  // ... campos existentes ...
  perfil_lead: LeadProfile | null;
  nicho_canonico: NichoCanonico | null;
  nicho_source: NichoSource | null;
  nicho_confidence: number | null;
  pacote_sugerido: PacoteSugerido | null;
  prioridade: Prioridade | null;
  has_instagram: boolean | null;
  classified_at: string | null;
};

export const LEAD_PROFILE_LABEL: Record<LeadProfile, string> = {
  hot_no_site: "Sem site validado",
  hot_bad_site: "Site ruim",
  warm: "Oportunidade média",
  cold: "Site ok",
  disqualified: "Desqualificado",
};

export const NICHO_LABEL: Record<NichoCanonico, string> = {
  dentista: "Odontologia",
  estetica: "Estética",
  salao_barbearia: "Salão / Barbearia",
  restaurante: "Restaurante / Bar",
  petshop_vet: "Pet shop / Vet",
  academia: "Academia",
  contabilidade: "Contabilidade",
  imobiliaria: "Imobiliária",
  loja_roupas: "Loja de roupas",
  auto_escola: "Autoescola",
  advocacia: "Advocacia",
  industria: "Indústria",
  clinica_medica: "Clínica médica",
  escola_curso: "Escola / Curso",
  outros: "Outros",
};
```

- [ ] **Step 2: Adicionar métodos em `api.ts`**

Abrir `frontend/src/lib/api.ts`. Adicionar métodos (seguindo o padrão `fetchAPI`):

```typescript
export async function classifyLeads(params: {
  scope: "unclassified" | "all" | "by_job" | "by_status";
  scope_filter?: Record<string, any>;
  force?: boolean;
}): Promise<{ id: number }> {
  return fetchAPI("/api/pipeline/classify", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function reclassifyLead(id: number, force = true): Promise<Lead> {
  return fetchAPI(`/api/leads/${id}/reclassify`, {
    method: "POST",
    body: JSON.stringify({ force }),
  });
}

export async function getLeadsForReview(params?: {
  page?: number;
  per_page?: number;
}): Promise<{ leads: Lead[]; total: number; page: number; per_page: number }> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.per_page) qs.set("per_page", String(params.per_page));
  return fetchAPI(`/api/leads/review?${qs}`);
}
```

Também atualizar o método de listar leads (provavelmente `listLeads` ou `getLeads`) pra aceitar `perfil_lead`, `nicho_canonico` e o novo valor de `order_by="prioridade"`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "feat(frontend): types and API methods for classification"
```

---

### Task 18: Componente `ProfileBadge`

**Files:**
- Create: `frontend/src/components/ui/profile-badge.tsx`

- [ ] **Step 1: Implementar componente**

Criar `frontend/src/components/ui/profile-badge.tsx`:

```tsx
import { cn } from "@/lib/utils";
import { LEAD_PROFILE_LABEL, type LeadProfile } from "@/lib/types";

const STYLES: Record<LeadProfile, { bg: string; text: string; emoji?: string }> = {
  hot_no_site:   { bg: "bg-[var(--score-hot)]/15",  text: "text-[var(--score-hot)]",  emoji: "🔥" },
  hot_bad_site:  { bg: "bg-[var(--score-hot)]/15",  text: "text-[var(--score-hot)]",  emoji: "🔥" },
  warm:          { bg: "bg-[var(--score-warm)]/15", text: "text-[var(--score-warm)]" },
  cold:          { bg: "bg-[var(--score-cool)]/15", text: "text-[var(--score-cool)]" },
  disqualified:  { bg: "bg-[var(--surface-2)]",     text: "text-[var(--text-muted)]" },
};

export function ProfileBadge({
  profile,
  showEmoji = true,
  size = "sm",
  className,
}: {
  profile: LeadProfile | null | undefined;
  showEmoji?: boolean;
  size?: "sm" | "md";
  className?: string;
}) {
  if (!profile) return null;
  const style = STYLES[profile];
  const label = LEAD_PROFILE_LABEL[profile];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md font-medium",
        size === "sm" ? "px-1.5 py-0.5 text-[11px]" : "px-2 py-1 text-xs",
        style.bg,
        style.text,
        className,
      )}
      title={label}
    >
      {showEmoji && style.emoji && <span>{style.emoji}</span>}
      <span>{label}</span>
    </span>
  );
}
```

- [ ] **Step 2: Verificar build**

```bash
cd frontend && npm run lint
```

Expected: sem errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/profile-badge.tsx
git commit -m "feat(ui): ProfileBadge primitive"
```

---

### Task 19: Kanban + Lead List — badge e filtros

**Files:**
- Modify: `frontend/src/components/kanban-board.tsx`
- Modify: `frontend/src/components/kanban-filters.tsx`
- Modify: `frontend/src/components/leads/la-master.tsx`

- [ ] **Step 1: Adicionar `<ProfileBadge>` no card do lead**

Em `kanban-board.tsx`, localizar o componente que renderiza cada card (provavelmente `LeadCard` ou inline). Adicionar:

```tsx
import { ProfileBadge } from "@/components/ui/profile-badge";

// dentro do JSX do card:
<div className="flex items-center gap-1">
  <ProfileBadge profile={lead.perfil_lead} size="sm" />
  {/* score existente */}
</div>
```

- [ ] **Step 2: Adicionar filtros em `kanban-filters.tsx`**

Localizar os dropdowns existentes (nicho/cidade). Adicionar:

```tsx
import { LEAD_PROFILE_LABEL, NICHO_LABEL } from "@/lib/types";

<Select value={filters.perfil_lead} onChange={(v) => setFilter("perfil_lead", v)}>
  <option value="">Todos os perfis</option>
  {Object.entries(LEAD_PROFILE_LABEL).map(([k, label]) => (
    <option key={k} value={k}>{label}</option>
  ))}
</Select>

<Select value={filters.nicho_canonico} onChange={(v) => setFilter("nicho_canonico", v)}>
  <option value="">Todos os nichos</option>
  {Object.entries(NICHO_LABEL).map(([k, label]) => (
    <option key={k} value={k}>{label}</option>
  ))}
</Select>
```

Adaptar pro componente `Select` existente no design system.

Propagar os filtros pra chamada `listLeads` (na função que fetcha os leads do kanban).

- [ ] **Step 3: Aplicar filtros equivalentes em `la-master.tsx`**

Abrir `frontend/src/components/leads/la-master.tsx`. Localizar a barra de filtros da lista de leads (dropdowns `status`, `nicho`, `cidade` existentes). Adicionar, seguindo o mesmo padrão, dois selects:

```tsx
import { LEAD_PROFILE_LABEL, NICHO_LABEL } from "@/lib/types";

// Dentro do JSX de filtros:
<select
  value={filters.perfil_lead ?? ""}
  onChange={(e) => setFilter("perfil_lead", e.target.value || null)}
>
  <option value="">Todos os perfis</option>
  {Object.entries(LEAD_PROFILE_LABEL).map(([k, label]) => (
    <option key={k} value={k}>{label}</option>
  ))}
</select>

<select
  value={filters.nicho_canonico ?? ""}
  onChange={(e) => setFilter("nicho_canonico", e.target.value || null)}
>
  <option value="">Todos os nichos</option>
  {Object.entries(NICHO_LABEL).map(([k, label]) => (
    <option key={k} value={k}>{label}</option>
  ))}
</select>
```

Propagar os filtros pro hook que fetcha leads (provavelmente `use-lead-app.ts` — adicionar `perfil_lead` e `nicho_canonico` ao params de `listLeads`). Persistir em localStorage seguindo padrão existente.

Em cada card da lista master, adicionar o `<ProfileBadge>` (análogo ao card do kanban):

```tsx
import { ProfileBadge } from "@/components/ui/profile-badge";

// No card:
<ProfileBadge profile={lead.perfil_lead} size="sm" />
```

- [ ] **Step 4: Testar visualmente**

```bash
cd frontend && npm run dev
```

Abrir http://localhost:3000/app/kanban e http://localhost:3000/app/leads. Validar em ambos:
- Badge aparece em cada card
- Filtro por perfil limita itens visíveis
- Filtro por nicho limita itens visíveis
- Filtros persistem em localStorage (recarregar página mantém escolha)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/kanban-board.tsx frontend/src/components/kanban-filters.tsx frontend/src/components/leads/la-master.tsx frontend/src/components/leads/use-lead-app.ts
git commit -m "feat(frontend): profile badge + filters in kanban and lead list"
```

---

### Task 20: Lead App — seção Classificação no rail

**Files:**
- Create: `frontend/src/components/leads/la-classification.tsx`
- Modify: `frontend/src/components/leads/la-header.tsx`
- Modify: `frontend/src/components/leads/la-rail.tsx`

- [ ] **Step 1: Criar `LaClassification`**

Criar `frontend/src/components/leads/la-classification.tsx`:

```tsx
"use client";

import { useState } from "react";
import { ProfileBadge } from "@/components/ui/profile-badge";
import {
  LEAD_PROFILE_LABEL, NICHO_LABEL,
  type Lead, type NichoCanonico,
} from "@/lib/types";
import { reclassifyLead } from "@/lib/api";

export function LaClassification({
  lead,
  onUpdated,
}: {
  lead: Lead;
  onUpdated: (lead: Lead) => void;
}) {
  const [loading, setLoading] = useState(false);

  async function handleReclassify() {
    setLoading(true);
    try {
      const updated = await reclassifyLead(lead.id);
      onUpdated(updated);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="la-rail-section">
      <header className="la-rail-section-header">
        <h4>Classificação</h4>
        <button
          className="la-btn-inline"
          disabled={loading}
          onClick={handleReclassify}
        >
          {loading ? "Re-classificando..." : "Re-classificar"}
        </button>
      </header>

      <dl className="la-classification-grid">
        <dt>Perfil</dt>
        <dd><ProfileBadge profile={lead.perfil_lead} size="md" /></dd>

        <dt>Nicho</dt>
        <dd>
          {lead.nicho_canonico && NICHO_LABEL[lead.nicho_canonico as NichoCanonico]}
          {lead.nicho_source && (
            <span className="la-source-tag" title={`Fonte: ${lead.nicho_source}`}>
              {lead.nicho_source}
            </span>
          )}
        </dd>

        <dt>Confiança</dt>
        <dd>
          <div className="la-confidence-bar">
            <div
              className="la-confidence-fill"
              style={{ width: `${(lead.nicho_confidence ?? 0) * 100}%` }}
            />
          </div>
          <span>{Math.round((lead.nicho_confidence ?? 0) * 100)}%</span>
        </dd>

        <dt>Pacote sugerido</dt>
        <dd>{lead.pacote_sugerido ?? "—"}</dd>

        <dt>Prioridade</dt>
        <dd>{lead.prioridade ?? "—"}</dd>
      </dl>
    </section>
  );
}
```

Adicionar estilos correspondentes em `lead-app.css` (seguir padrão existente `.la-rail-section`, etc).

- [ ] **Step 2: Badge no header**

Em `la-header.tsx`, adicionar `<ProfileBadge profile={lead.perfil_lead} size="md" />` ao lado do status pill.

- [ ] **Step 3: Embed em `la-rail.tsx`**

Importar e renderizar `<LaClassification lead={lead} onUpdated={onUpdated} />` no topo do rail.

- [ ] **Step 4: Testar visualmente**

Abrir `/app/leads/<id>`. Validar:
- Badge no header
- Seção classificação no rail
- Botão "Re-classificar" funciona

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/leads/
git commit -m "feat(leads): classification section in rail + reclassify button"
```

---

### Task 21: Pipeline controls — botão "Classificar"

**Files:**
- Create: `frontend/src/components/pipeline/classify-modal.tsx`
- Modify: `frontend/src/components/pipeline-controls.tsx`

- [ ] **Step 1: Criar modal**

Criar `frontend/src/components/pipeline/classify-modal.tsx`:

```tsx
"use client";

import { useState } from "react";
import { classifyLeads } from "@/lib/api";

export function ClassifyModal({
  onStarted,
  onClose,
}: {
  onStarted: (jobId: number) => void;
  onClose: () => void;
}) {
  const [scope, setScope] = useState<"unclassified" | "all">("unclassified");
  const [force, setForce] = useState(false);
  const [busy, setBusy] = useState(false);

  async function handleStart() {
    setBusy(true);
    try {
      const { id } = await classifyLeads({ scope, force });
      onStarted(id);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-body" onClick={(e) => e.stopPropagation()}>
        <h3>Classificar leads</h3>
        <label>
          <span>Escopo</span>
          <select value={scope} onChange={(e) => setScope(e.target.value as any)}>
            <option value="unclassified">Apenas não classificados</option>
            <option value="all">Todos os leads</option>
          </select>
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={force}
            onChange={(e) => setForce(e.target.checked)}
          />
          Forçar re-classificação de nicho
        </label>
        <div className="modal-actions">
          <button onClick={onClose}>Cancelar</button>
          <button className="primary" disabled={busy} onClick={handleStart}>
            {busy ? "Iniciando..." : "Iniciar"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Adicionar botão em `pipeline-controls.tsx`**

Importar `ClassifyModal`. Adicionar o 5º botão + state do modal (seguir padrão dos outros 4 botões existentes).

- [ ] **Step 3: Testar visualmente**

Abrir `/app/pipeline`. Clicar no botão "Classificar". Validar modal abre, botão "Iniciar" cria job, progresso aparece via SSE.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/pipeline/ frontend/src/components/pipeline-controls.tsx
git commit -m "feat(pipeline): classify backlog button and modal"
```

---

### Task 22: Dashboard — widgets de distribuição

**Files:**
- Create: `frontend/src/components/dashboard/profile-distribution.tsx`
- Create: `frontend/src/components/dashboard/nicho-distribution.tsx`
- Modify: `frontend/src/app/app/dashboard/page.tsx`
- Modify: `backend/app/routers/dashboard.py` (expor agregados)

- [ ] **Step 1: Adicionar agregados no backend**

Em `backend/app/routers/dashboard.py`, no handler de `/stats`, adicionar:

```python
from sqlalchemy import func

# Dentro do handler, após os aggregates existentes:
profile_dist_rows = (
    db.query(Lead.perfil_lead, func.count(Lead.id))
    .filter(Lead.perfil_lead.isnot(None))
    .group_by(Lead.perfil_lead)
    .all()
)
profile_distribution = {row[0]: row[1] for row in profile_dist_rows}

nicho_dist_rows = (
    db.query(Lead.nicho_canonico, func.count(Lead.id))
    .filter(Lead.nicho_canonico.isnot(None))
    .group_by(Lead.nicho_canonico)
    .all()
)
nicho_distribution = {row[0]: row[1] for row in nicho_dist_rows}

# Adicionar ao dict de retorno:
return {
    # ... campos existentes ...
    "profile_distribution": profile_distribution,
    "nicho_distribution": nicho_distribution,
}
```

- [ ] **Step 2: Criar componente `profile-distribution.tsx`**

```tsx
import Link from "next/link";
import { LEAD_PROFILE_LABEL, type LeadProfile } from "@/lib/types";

export function ProfileDistribution({
  data,
}: {
  data: Record<string, number>;
}) {
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  const order: LeadProfile[] = [
    "hot_no_site", "hot_bad_site", "warm", "cold", "disqualified",
  ];

  return (
    <div className="card">
      <h3>Distribuição por perfil</h3>
      <ul className="distribution-list">
        {order.map((p) => {
          const count = data[p] ?? 0;
          const pct = total > 0 ? Math.round((count / total) * 100) : 0;
          return (
            <li key={p}>
              <Link href={`/app/kanban?perfil_lead=${p}`}>
                <span className="label">{LEAD_PROFILE_LABEL[p]}</span>
                <div className="bar">
                  <div className="fill" style={{ width: `${pct}%` }} />
                </div>
                <span className="count">{count} ({pct}%)</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
```

- [ ] **Step 3: Criar `nicho-distribution.tsx` (análogo)**

Mesmo padrão, mas com `NICHO_LABEL` e ordenando do maior pro menor count. Limitar top 10 + botão "expandir".

- [ ] **Step 4: Embed na dashboard page**

Em `frontend/src/app/app/dashboard/page.tsx`, adicionar no grid:

```tsx
<ProfileDistribution data={stats.profile_distribution ?? {}} />
<NichoDistribution data={stats.nicho_distribution ?? {}} />
```

- [ ] **Step 5: Validar visualmente**

Abrir `/app/dashboard`. Validar widgets aparecem com dados reais.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/dashboard/ frontend/src/app/app/dashboard/ backend/app/routers/dashboard.py
git commit -m "feat(dashboard): profile and nicho distribution widgets"
```

---

### Task 23: Página de revisão `/app/leads/review`

**Files:**
- Create: `frontend/src/app/app/leads/review/page.tsx`
- Create: `frontend/src/app/app/leads/review/review-table.tsx`
- Modify: `frontend/src/components/app-sidebar.tsx`

- [ ] **Step 1: Implementar tabela (client component)**

Criar `frontend/src/app/app/leads/review/review-table.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { getLeadsForReview, reclassifyLead, updateLead } from "@/lib/api";
import { NICHO_LABEL, type Lead, type NichoCanonico } from "@/lib/types";

export function ReviewTable() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const r = await getLeadsForReview({ per_page: 100 });
      setLeads(r.leads);
      setLoading(false);
    })();
  }, []);

  async function setNicho(lead: Lead, nicho: NichoCanonico) {
    const updated = await updateLead(lead.id, { nicho_canonico: nicho });
    setLeads((ls) => ls.map((l) => (l.id === lead.id ? updated : l)));
  }

  async function reclassify(lead: Lead) {
    const updated = await reclassifyLead(lead.id);
    setLeads((ls) => ls.map((l) => (l.id === lead.id ? updated : l)));
  }

  if (loading) return <p>Carregando...</p>;
  if (!leads.length) return <p>Nenhum lead pendente de revisão.</p>;

  return (
    <table className="review-table">
      <thead>
        <tr>
          <th>Nome</th>
          <th>Nicho bruto</th>
          <th>Sugestão</th>
          <th>Confiança</th>
          <th>Ações</th>
        </tr>
      </thead>
      <tbody>
        {leads.map((l) => (
          <tr key={l.id}>
            <td>{l.nome}</td>
            <td><code>{l.nicho || l.categoria || "—"}</code></td>
            <td>
              {l.nicho_canonico ? NICHO_LABEL[l.nicho_canonico as NichoCanonico] : "—"}
            </td>
            <td>{Math.round((l.nicho_confidence ?? 0) * 100)}%</td>
            <td>
              <select
                value={l.nicho_canonico ?? "outros"}
                onChange={(e) => setNicho(l, e.target.value as NichoCanonico)}
              >
                {Object.entries(NICHO_LABEL).map(([k, lbl]) => (
                  <option key={k} value={k}>{lbl}</option>
                ))}
              </select>
              <button onClick={() => reclassify(l)}>Re-classificar</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 2: Implementar page server component**

Criar `frontend/src/app/app/leads/review/page.tsx`:

```tsx
import { ReviewTable } from "./review-table";

export default function ReviewPage() {
  return (
    <div className="page-container">
      <h1>Revisão de nichos</h1>
      <p className="page-subtitle">
        Leads com classificação incerta ou que caíram em "outros" — revise manualmente.
      </p>
      <ReviewTable />
    </div>
  );
}
```

- [ ] **Step 3: Link no sidebar**

Em `app-sidebar.tsx`, adicionar item de nav "Revisão de nichos". Usar `getLeadsForReview` pra buscar contagem e exibir badge ao lado do nome.

- [ ] **Step 4: Testar visualmente**

Abrir `/app/leads/review`. Validar lista carrega, edição inline funciona, botão re-classify funciona.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/app/leads/review/ frontend/src/components/app-sidebar.tsx
git commit -m "feat(leads): manual review page for outros/failed/low-confidence"
```

---

## Fase 5 — QA manual e aceite

### Task 24: QA manual em amostra real

**Files:**
- Create: `docs/superpowers/plans/2026-04-20-lead-profile-classification-qa.md`

- [ ] **Step 1: Rodar batch job sobre backlog**

Na UI: `/app/pipeline` → "Classificar" → "Apenas não classificados" → Iniciar.

Acompanhar SSE. Verificar ao final: `results.ok + results.failed == total`.

- [ ] **Step 2: Exportar 20 leads aleatórios pra planilha**

```bash
docker compose exec api python -c "
import random
from app.database import SessionLocal
from app.models import Lead

db = SessionLocal()
leads = db.query(Lead).filter(Lead.perfil_lead.isnot(None)).all()
sample = random.sample(leads, min(20, len(leads)))
for l in sample:
    print(f'{l.id}|{l.nome}|{l.nicho}|{l.rating}|{l.reviews_count}|{l.perfil_lead}|{l.nicho_canonico}')
"
```

- [ ] **Step 3: Revisar manualmente**

Criar `docs/superpowers/plans/2026-04-20-lead-profile-classification-qa.md` com a lista, e marcar cada lead como ✅/❌ pro perfil e pro nicho.

Critérios de aceite:
- ≥18/20 perfis corretos
- ≤4/20 caem em `outros`
- Se >10/20 dos `outros` deveriam ter bucket → taxonomia precisa ajuste (abrir issue, ajustar `NICHO_ALIASES`, re-rodar)

- [ ] **Step 4: Verificar distribuição no dashboard**

Abrir `/app/dashboard`. Validar:
- Widget perfil mostra distribuição com 5 buckets
- Widget nicho mostra top 10 + `outros` expansível
- Distribuição de `outros` no total ≤ 20%

- [ ] **Step 5: Commit do QA report**

```bash
git add docs/superpowers/plans/2026-04-20-lead-profile-classification-qa.md
git commit -m "docs: QA report for lead classification launch"
```

---

### Task 25: Checklist final de aceite

- [ ] **Bloco funcional**
  - [ ] 100% dos leads com `perfil_lead IS NOT NULL` no DB após batch
  - [ ] Amostra 20 leads: ≥18 perfis corretos
  - [ ] ≤ 20% em `outros`
- [ ] **Bloco operacional**
  - [ ] Batch 100+ leads roda sem travar
  - [ ] `pytest` verde (inclusive `test_classification_resilience.py`)
  - [ ] Idempotência: rodar 2× = mesmo resultado
  - [ ] Circuit breaker dispara em teste forçado
- [ ] **Bloco usável**
  - [ ] Kanban filtrável por perfil + nicho
  - [ ] Lead App exibe badge + edição manual + re-classify funcional
  - [ ] Dashboard 2 widgets funcionando
  - [ ] `/app/leads/review` lista e permite ação inline
  - [ ] Pipeline tem botão "Classificar" funcional

Quando todos marcados, abrir PR e transicionar para **spec 2 — LP Conversion Tracking**.

---

## Notas para executor

1. **Ordem das fases não é estritamente sequencial** — Fase 1 é pré-req de Fase 2, que é pré-req de Fase 3. Fase 4 (frontend) depende da Fase 3. Dentro de cada fase, as tasks têm dependência linear.

2. **Dois worktrees sugeridos**:
   - `backend-classification` — Fases 1-3 (tasks 1-16)
   - `frontend-classification` — Fase 4 (tasks 17-23) — pode começar depois da Task 15 estar mergeada

3. **Testes sempre rodam SQLite in-memory** via `conftest.py` existente. Batch job em background precisa lidar com sessão — o padrão `SessionLocal()` novo já é o adotado.

4. **Ao adicionar enums ao DB via `String(30)`**: sempre validar no código Python antes de persistir (usar `LeadProfile(val)` ou `NichoCanonico(val)` — levanta ValueError se inválido; tratar antes de chegar ao ORM).

5. **Custos LLM**: batch de 100 leads com ~30% caindo em camada 3 (LLM) ≈ 30 chamadas Haiku × R$0.001 = R$0.03. Prompt caching não implementado (out of scope — considerar em spec futura quando escalar).

6. **Observabilidade**: logs via stdout; nenhuma infra nova de métricas. Spec separada quando necessário.
