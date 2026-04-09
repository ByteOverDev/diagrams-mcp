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
