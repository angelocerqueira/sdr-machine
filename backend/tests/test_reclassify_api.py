def test_reclassify_single_lead(client, sample_lead):
    resp = client.post(f"/api/leads/{sample_lead.id}/reclassify")
    assert resp.status_code == 200
    body = resp.json()
    assert body["perfil_lead"] is not None
    assert body["nicho_canonico"] is not None


def test_reclassify_404_on_missing(client):
    resp = client.post("/api/leads/999999/reclassify")
    assert resp.status_code == 404


def test_reclassify_force_false_preserves_manual_nicho(client, db_session):
    from app.models import Lead
    lead = Lead(
        nome="Oficina Teste", telefone="11", rating=4.5, reviews_count=50,
        nicho="Mecanica automotiva",
        nicho_canonico="advocacia",  # intentionally wrong — pretend user fixed it
        nicho_source="manual", nicho_confidence=1.0,
    )
    db_session.add(lead)
    db_session.commit()
    lead_id = lead.id

    resp = client.post(
        f"/api/leads/{lead_id}/reclassify",
        json={"force": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["nicho_canonico"] == "advocacia"  # NOT overwritten
    assert body["nicho_source"] == "manual"
    assert body["nicho_confidence"] == 1.0
    # But perfil_lead SHOULD still be recomputed (force only gates nicho preservation)
    assert body["perfil_lead"] is not None


def test_reclassify_force_true_overrides_manual(client, db_session):
    from app.models import Lead
    lead = Lead(
        nome="Pizzaria Bella", telefone="11", rating=4.5, reviews_count=60,
        nicho="Pizzaria",
        nicho_canonico="advocacia",  # user-set but wrong for classifier
        nicho_source="manual", nicho_confidence=1.0,
    )
    db_session.add(lead)
    db_session.commit()
    lead_id = lead.id

    resp = client.post(
        f"/api/leads/{lead_id}/reclassify",
        json={"force": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    # With force=True, classifier output wins: "Pizzaria" → restaurante
    assert body["nicho_canonico"] == "restaurante"
    assert body["nicho_source"] != "manual"


def test_patch_with_nicho_canonico_marks_manual_source(client, sample_lead):
    resp = client.patch(
        f"/api/leads/{sample_lead.id}",
        json={"nicho_canonico": "dentista"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["nicho_canonico"] == "dentista"
    assert body["nicho_source"] == "manual"
    assert body["nicho_confidence"] == 1.0
