from starlette.testclient import TestClient

from diagrams_mcp.server import mcp


def test_health_endpoint_returns_ok():
    """The /health endpoint returns HTTP 200 with status ok."""
    app = mcp.http_app()
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
