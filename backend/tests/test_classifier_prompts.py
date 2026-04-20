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
