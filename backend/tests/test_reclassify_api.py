def test_reclassify_single_lead(client, sample_lead):
    resp = client.post(f"/api/leads/{sample_lead.id}/reclassify")
    assert resp.status_code == 200
    body = resp.json()
    assert body["perfil_lead"] is not None
    assert body["nicho_canonico"] is not None


def test_reclassify_404_on_missing(client):
    resp = client.post("/api/leads/999999/reclassify")
    assert resp.status_code == 404


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
