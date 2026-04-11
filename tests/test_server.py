import asyncio

from mcp import McpError
from starlette.testclient import TestClient

from diagrams_mcp.image_store import image_store
from diagrams_mcp.server import mcp


def test_health_endpoint_returns_ok():
    """The /health endpoint returns HTTP 200 with status ok."""
    app = mcp.http_app()
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_serve_image_returns_png():
    """GET /images/{token} returns the stored PNG with correct headers."""
    token = image_store.store(b"\x89PNG\r\n\x1a\nfake", "my_diagram")
    app = mcp.http_app()
    with TestClient(app) as client:
        response = client.get(f"/images/{token}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert 'filename="my_diagram.png"' in response.headers["content-disposition"]
        assert response.content == b"\x89PNG\r\n\x1a\nfake"


def test_serve_image_unknown_token_returns_404():
    """GET /images/{bad_token} returns 404."""
    app = mcp.http_app()
    with TestClient(app) as client:
        response = client.get("/images/nonexistent-token")
        assert response.status_code == 404


def test_serve_image_expired_returns_404():
    """GET /images/{token} returns 404 for expired images."""
    token = image_store.store(b"data", "expired", ttl=0)
    app = mcp.http_app()
    with TestClient(app) as client:
        response = client.get(f"/images/{token}")
        assert response.status_code == 404


def test_serve_image_returns_svg():
    """GET /images/{token} returns SVG with correct headers when stored as svg."""
    token = image_store.store(b"<svg></svg>", "my_diagram", fmt="svg")
    app = mcp.http_app()
    with TestClient(app) as client:
        response = client.get(f"/images/{token}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"
        assert 'filename="my_diagram.svg"' in response.headers["content-disposition"]


def test_serve_image_returns_pdf():
    """GET /images/{token} returns PDF with correct headers when stored as pdf."""
    token = image_store.store(b"%PDF-1.4 fake", "my_diagram", fmt="pdf")
    app = mcp.http_app()
    with TestClient(app) as client:
        response = client.get(f"/images/{token}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert 'filename="my_diagram.pdf"' in response.headers["content-disposition"]


def test_equivalence_tools_registered():
    """find_equivalent and list_categories tools are mounted on the root server."""
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert "find_equivalent" in names
    assert "list_categories" in names


def test_rate_limiting_middleware_is_registered():
    """RateLimitingMiddleware is present in the root server's middleware chain."""
    from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware

    middleware_types = [type(m) for m in mcp.middleware]
    assert RateLimitingMiddleware in middleware_types


def test_rate_limiting_rejects_after_burst():
    """After exhausting burst capacity, further requests are rejected with McpError."""
    from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware

    # Read burst_capacity from the actual middleware instance
    rl = next(m for m in mcp.middleware if isinstance(m, RateLimitingMiddleware))
    burst = rl.burst_capacity

    async def fire_concurrent():
        # Schedule more concurrent calls than the burst capacity allows
        tasks = [mcp.call_tool("list_providers") for _ in range(burst + 1)]
        return await asyncio.gather(*tasks, return_exceptions=True)

    results = asyncio.run(fire_concurrent())

    # At least one call should have been rejected with McpError
    errors = [r for r in results if isinstance(r, McpError)]
    assert errors, f"Expected at least 1 McpError among {len(results)} results"
