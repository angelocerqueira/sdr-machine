from app.mcp.server import build_mcp_server


def test_build_mcp_server_returns_fastmcp():
    server = build_mcp_server()
    from mcp.server.fastmcp import FastMCP
    assert isinstance(server, FastMCP)


def test_build_mcp_server_name():
    server = build_mcp_server()
    assert server.name == "sdr-machine"
