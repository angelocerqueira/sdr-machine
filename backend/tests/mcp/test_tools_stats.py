import asyncio
from unittest.mock import Mock

from mcp.server.auth.provider import AccessToken
from app.models import Lead
from app.mcp.tools_stats import dashboard_stats, conversion_funnel


def _ctx():
    ctx = Mock()
    user = Mock()
    user.access_token = AccessToken(
        token="x" * 64, client_id="mcp-1",
        scopes=["mcp:workspace:1"], expires_at=None, resource=None,
    )
    ctx.request_context.request.user = user
    return ctx


def test_dashboard_stats_empty(db):
    result = asyncio.run(dashboard_stats(_ctx()))
    assert result.total_leads == 0
    assert result.by_status == {}


def test_dashboard_stats_aggregates(db):
    db.add_all([
        Lead(nome="A", telefone="x", status="scraped", opportunity_score=40),
        Lead(nome="B", telefone="y", status="enriched", opportunity_score=60),
        Lead(nome="C", telefone="z", status="enriched", opportunity_score=80),
    ])
    db.commit()
    result = asyncio.run(dashboard_stats(_ctx()))
    assert result.total_leads == 3
    assert result.by_status["enriched"] == 2
    assert result.by_status["scraped"] == 1
    assert result.avg_score == 60.0


def test_conversion_funnel_returns_period_data(db):
    result = asyncio.run(conversion_funnel(_ctx(), period="7d"))
    assert isinstance(result, dict)
    assert result["period"] == "7d"
