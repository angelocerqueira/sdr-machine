import asyncio
from unittest.mock import Mock

from mcp.server.auth.provider import AccessToken

from app.models import Lead
from app.mcp.tools_leads import list_leads, get_lead, list_landing_pages


def _ctx(workspace_id: int = 1):
    ctx = Mock()
    user = Mock()
    user.access_token = AccessToken(
        token="x" * 64, client_id=f"mcp-{workspace_id}",
        scopes=[f"mcp:workspace:{workspace_id}"], expires_at=None, resource=None,
    )
    ctx.request_context.request.user = user
    return ctx


def test_list_leads_empty(db):
    result = asyncio.run(list_leads(_ctx(), filter=None, limit=20, offset=0))
    assert result.total == 0
    assert result.items == []


def test_list_leads_returns_all(db):
    db.add_all([
        Lead(nome="A", telefone="44999990000", status="scraped"),
        Lead(nome="B", telefone="44888880000", status="enriched"),
    ])
    db.commit()
    result = asyncio.run(list_leads(_ctx(), filter=None, limit=20, offset=0))
    assert result.total == 2
    assert {item.nome for item in result.items} == {"A", "B"}


def test_list_leads_filter_status(db):
    db.add_all([
        Lead(nome="A", telefone="x", status="scraped"),
        Lead(nome="B", telefone="y", status="enriched"),
    ])
    db.commit()
    result = asyncio.run(list_leads(_ctx(), filter={"status": "scraped"}, limit=20, offset=0))
    assert result.total == 1
    assert result.items[0].nome == "A"


def test_list_leads_filter_score_min(db):
    db.add_all([
        Lead(nome="Low", telefone="x", status="scraped", opportunity_score=30),
        Lead(nome="High", telefone="y", status="scraped", opportunity_score=85),
    ])
    db.commit()
    result = asyncio.run(list_leads(_ctx(), filter={"score_min": 70}, limit=20, offset=0))
    assert result.total == 1
    assert result.items[0].nome == "High"


def test_list_leads_search(db):
    db.add_all([
        Lead(nome="Padaria Central", telefone="x", status="scraped"),
        Lead(nome="Auto Posto", telefone="y", status="scraped"),
    ])
    db.commit()
    result = asyncio.run(list_leads(_ctx(), filter={"search": "padaria"}, limit=20, offset=0))
    assert result.total == 1


def test_list_leads_pagination(db):
    for i in range(5):
        db.add(Lead(nome=f"L{i}", telefone=f"x{i}", status="scraped"))
    db.commit()
    p1 = asyncio.run(list_leads(_ctx(), filter=None, limit=2, offset=0))
    p2 = asyncio.run(list_leads(_ctx(), filter=None, limit=2, offset=2))
    assert len(p1.items) == 2
    assert len(p2.items) == 2
    assert p1.total == 5
    assert {x.id for x in p1.items} != {x.id for x in p2.items}


def test_get_lead_returns_full(db):
    lead = Lead(
        nome="Detail Co", telefone="44999990000", email="a@b.com",
        website="https://x.com", nicho="dentista", cidade="Chapecó",
        status="enriched", opportunity_score=75,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    result = asyncio.run(get_lead(_ctx(), id=lead.id))
    assert result is not None
    assert result.id == lead.id
    assert result.email == "a@b.com"
    assert result.opportunity_score == 75


def test_get_lead_not_found(db):
    result = asyncio.run(get_lead(_ctx(), id=9999))
    assert result is None


def test_list_landing_pages_respects_limit(db):
    from app.models import LandingPage
    lead = Lead(nome="X", telefone="x", status="enriched")
    db.add(lead)
    db.commit()
    db.refresh(lead)
    for i in range(5):
        db.add(LandingPage(lead_id=lead.id, version=i+1, html="<p>x</p>"))
    db.commit()

    result = asyncio.run(list_landing_pages(_ctx(), lead_id=lead.id, limit=3))
    assert len(result) == 3
