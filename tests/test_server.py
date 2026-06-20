import asyncio

from starlette.testclient import TestClient

from diagrams_mcp.image_store import image_store
from diagrams_mcp.server import create_test_http_app, mcp


def test_health_endpoint_returns_ok():
    """The /health endpoint returns HTTP 200 with shields.io-compatible JSON."""
    app = create_test_http_app()
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["schemaVersion"] == 1
        assert data["message"] == "up"


def test_serve_image_returns_png():
    """GET /images/{token} returns the stored PNG with correct headers."""
    token = image_store.store(b"\x89PNG\r\n\x1a\nfake", "my_diagram")
    app = create_test_http_app()
    with TestClient(app) as client:
        response = client.get(f"/images/{token}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert 'filename="my_diagram.png"' in response.headers["content-disposition"]
        assert response.content == b"\x89PNG\r\n\x1a\nfake"


def test_serve_image_with_file_store(monkeypatch, tmp_path):
    """GET /images/{token} can serve outputs from the active storage backend."""
    import diagrams_mcp.server as server_module
    from diagrams_mcp.image_store import FileImageStore

    store = FileImageStore(tmp_path)
    token = store.store(b"\x89PNG\r\n\x1a\nfake", "file")
    monkeypatch.setattr(server_module, "output_store", store)
    app = create_test_http_app()
    with TestClient(app) as client:
        response = client.get(f"/images/{token}")
        assert response.status_code == 200
        assert response.content == b"\x89PNG\r\n\x1a\nfake"


def test_serve_image_sanitizes_non_ascii_filename():
    """Content-Disposition must remain latin-1 encodable for Starlette headers."""
    token = image_store.store(b"\x89PNG\r\n\x1a\nfake", "діаграма")
    app = create_test_http_app()
    with TestClient(app) as client:
        response = client.get(f"/images/{token}")
        assert response.status_code == 200
        assert response.headers["content-disposition"] == 'attachment; filename="image.png"'


def test_serve_image_unknown_token_returns_404():
    """GET /images/{bad_token} returns 404."""
    app = create_test_http_app()
    with TestClient(app) as client:
        response = client.get("/images/nonexistent-token")
        assert response.status_code == 404


def test_serve_image_expired_returns_404():
    """GET /images/{token} returns 404 for expired images."""
    token = image_store.store(b"data", "expired", ttl=0)
    app = create_test_http_app()
    with TestClient(app) as client:
        response = client.get(f"/images/{token}")
        assert response.status_code == 404


def test_serve_image_returns_svg():
    """GET /images/{token} returns SVG with correct headers when stored as svg."""
    token = image_store.store(b"<svg></svg>", "my_diagram", fmt="svg")
    app = create_test_http_app()
    with TestClient(app) as client:
        response = client.get(f"/images/{token}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"
        assert 'filename="my_diagram.svg"' in response.headers["content-disposition"]


def test_serve_image_returns_pdf():
    """GET /images/{token} returns PDF with correct headers when stored as pdf."""
    token = image_store.store(b"%PDF-1.4 fake", "my_diagram", fmt="pdf")
    app = create_test_http_app()
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
