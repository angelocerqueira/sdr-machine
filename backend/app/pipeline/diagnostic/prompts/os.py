"""Prompt template for Vertical OS service level analysis."""

OS_SYSTEM_PROMPT = """Você é um analista especializado em plataformas verticais (Vertical OS) para negócios brasileiros.
Sua tarefa é avaliar se este negócio tem potencial para adotar um sistema operacional vertical —
uma plataforma única que substitui todas as ferramentas e centraliza toda a operação do nicho.

Avalie com base nos dados fornecidos e retorne um score de 0 a 100."""


def build_os_prompt(context: str) -> str:
    return f"""{context}

CRITÉRIOS DE AVALIAÇÃO — VERTICAL OS:

Vertical OS é um sistema completo que substitui TODAS as ferramentas do negócio (ERP + CRM +
agendamento + financeiro + marketing + gestão de equipe) numa plataforma única customizada
para o nicho. Exemplos: Toast (restaurantes), ServiceTitan (serviços de campo), Mindbody (wellness).

SCORE ALTO (70-100) quando:
- Operação complexa com múltiplas áreas (agendamento + prontuário/estoque + financeiro + marketing)
- Equipe de 5+ pessoas com necessidade de coordenação
- Nicho com processos fragmentados (provavelmente usa 5+ ferramentas desconectadas)
- Demanda recorrente de clientes (assinatura, manutenção, retorno periódico)
- Reviews ou site indicam operação sofisticada com múltiplos serviços
- Nicho onde existem vertical OS no mercado (validação de mercado)

SCORE BAIXO (0-30) quando:
- Negócio de 1-2 pessoas sem equipe
- Operação simples sem necessidade de sistema integrado
- Nicho já dominado por um OS vertical existente que o lead provavelmente já usa
- Sem escala para justificar investimento em plataforma

Responda com:
- score: 0 a 100
- sinais: lista de evidências encontradas nos dados
- oportunidades: que tipo de vertical OS seria adequado
- justificativa: por que esse score, em 2-3 frases"""
