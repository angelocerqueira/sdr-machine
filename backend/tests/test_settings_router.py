"""Tests for GET/PUT /api/workspace/{profile,targeting}.

Parcial — só profile + targeting nesta task.
"""


def test_profile_get_empty_returns_defaults(client):
    res = client.get("/api/workspace/profile")
    assert res.status_code == 200
    body = res.json()
    assert body["business_name"] is None
    assert body["legal_basis"] == "legitimo_interesse_b2b"


def test_profile_put_upsert(client):
    res = client.put("/api/workspace/profile", json={
        "business_name": "Acme",
        "your_name": "Angelo",
        "your_email": "a@a.com",
        "your_whatsapp": "5549999",
        "your_website": "https://a.com",
    })
    assert res.status_code == 200
    assert res.json()["business_name"] == "Acme"

    # second PUT updates
    res = client.put("/api/workspace/profile", json={"business_name": "Acme 2"})
    assert res.json()["business_name"] == "Acme 2"
    # other fields preserved
    assert res.json()["your_name"] == "Angelo"


def test_targeting_get_empty(client):
    res = client.get("/api/workspace/targeting")
    assert res.status_code == 200
    body = res.json()
    assert body["target_niches"] == []
    assert body["target_cities"] == []


def test_targeting_put(client):
    res = client.put("/api/workspace/targeting", json={
        "target_niches": ["dentista", "pet shop"],
        "target_cities": ["Chapecó SC"],
        "min_rating": 4.0,
        "max_results_per_search": 50,
        "opportunity_score_threshold": 40,
    })
    assert res.status_code == 200
    assert res.json()["min_rating"] == 4.0
