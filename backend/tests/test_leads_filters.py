from app.models import Lead


def test_filter_by_perfil_lead(client, db_session):
    db_session.add(Lead(nome="A", telefone="1", perfil_lead="hot_no_site"))
    db_session.add(Lead(nome="B", telefone="2", perfil_lead="warm"))
    db_session.commit()

    resp = client.get("/api/leads?perfil_lead=hot_no_site")
    assert resp.status_code == 200
    names = [l["nome"] for l in resp.json()["items"]]
    assert names == ["A"]


def test_filter_by_nicho_canonico(client, db_session):
    db_session.add(Lead(nome="X", telefone="1", nicho_canonico="dentista"))
    db_session.add(Lead(nome="Y", telefone="2", nicho_canonico="restaurante"))
    db_session.commit()

    resp = client.get("/api/leads?nicho_canonico=dentista")
    assert resp.status_code == 200
    names = [l["nome"] for l in resp.json()["items"]]
    assert names == ["X"]


def test_order_by_prioridade(client, db_session):
    db_session.add(Lead(nome="H", telefone="1", prioridade="maxima"))
    db_session.add(Lead(nome="W", telefone="2", prioridade="media"))
    db_session.add(Lead(nome="D", telefone="3", prioridade="pular"))
    db_session.commit()

    resp = client.get("/api/leads?order_by=prioridade")
    assert resp.status_code == 200
    names = [l["nome"] for l in resp.json()["items"]]
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
    db_session.add(Lead(
        nome="Low conf", telefone="3",
        nicho_canonico="academia", nicho_source="llm_inferred",
        nicho_confidence=0.3,
    ))
    db_session.commit()

    resp = client.get("/api/leads/review")
    assert resp.status_code == 200
    names = [l["nome"] for l in resp.json()["items"]]
    assert "In review" in names
    assert "Low conf" in names
    assert "OK" not in names
