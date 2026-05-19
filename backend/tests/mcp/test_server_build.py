from app.mcp.server import build_mcp_server


def test_build_mcp_server_returns_fastmcp():
    server = build_mcp_server()
    from mcp.server.fastmcp import FastMCP
    assert isinstance(server, FastMCP)


def test_build_mcp_server_name():
    server = build_mcp_server()
    assert server.name == "sdr-machine"


def test_server_has_all_read_tools():
    server = build_mcp_server()

    expected_tools = {
        "list_leads", "get_lead", "list_landing_pages", "get_lp_html",
        "list_conversations", "get_conversation",
        "list_jobs", "get_job",
        "dashboard_stats", "conversion_funnel",
        "workspace_profile", "workspace_targeting",
        "list_pending_actions",
    }
    # FastMCP API pra listar tools varia entre versões — descobrir o accessor.
    # Tentar múltiplos:
    registered: set[str] = set()
    for attr in ("_tools", "_tool_manager"):
        obj = getattr(server, attr, None)
        if obj is None:
            continue
        tools_attr = getattr(obj, "_tools", None) or getattr(obj, "tools", None)
        if isinstance(tools_attr, dict):
            registered = set(tools_attr.keys())
            break
    # Se não conseguiu introspectar, fallback: roda list_tools async
    if not registered:
        import asyncio
        tools = asyncio.run(server.list_tools())
        registered = {t.name for t in tools}

    missing = expected_tools - registered
    assert not missing, f"Tools missing: {missing}"


def test_server_has_all_write_tools():
    from app.mcp.server import build_mcp_server
    server = build_mcp_server()

    expected = {
        "update_lead_status", "update_lead_fields", "mark_conversation_read",
        "update_workspace_profile", "update_workspace_targeting",
        "prepare_send_message", "prepare_bulk_send", "prepare_delete_lead",
        "prepare_delete_conversations", "prepare_run_pipeline",
        "prepare_classify_leads", "prepare_generate_lps",
        "commit_action", "cancel_action",
    }

    registered = set()
    obj = getattr(server, "_tool_manager", None)
    if obj is not None:
        tools = getattr(obj, "_tools", None)
        if isinstance(tools, dict):
            registered = set(tools.keys())
    if not registered:
        import asyncio
        tools = asyncio.run(server.list_tools())
        registered = {t.name for t in tools}

    missing = expected - registered
    assert not missing, f"Tools missing: {missing}"
