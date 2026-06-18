import base64
import socket

import pytest
from fastmcp.exceptions import ToolError
from starlette.testclient import TestClient

from diagrams_mcp.renderer import RemoteRenderer, RenderRequest, RenderResult, render_from_payload
from diagrams_mcp.renderer_service import _bind_dual_stack_sockets, app

_PNG = b"\x89PNG\r\n\x1a\nfake"


def test_render_from_payload_returns_structured_error_for_bad_request():
    result = render_from_payload({})
    assert result["ok"] is False
    assert "error" in result
    assert "errorType" in result


def test_renderer_service_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "diagrams-renderer"


def test_renderer_service_returns_structured_render_error():
    with TestClient(app) as client:
        response = client.post("/render", json={})
    assert response.status_code == 400
    assert response.json()["ok"] is False


def test_renderer_service_can_bind_ipv4_and_ipv6():
    try:
        sockets = _bind_dual_stack_sockets(0)
    except OSError as exc:
        pytest.skip(f"dual-stack bind unavailable: {exc}")
    try:
        assert {sock.family for sock in sockets} == {socket.AF_INET, socket.AF_INET6}
        assert len({sock.getsockname()[1] for sock in sockets}) == 1
    finally:
        for sock in sockets:
            sock.close()


def test_remote_renderer_decodes_success(monkeypatch):
    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok": true, "format": "png", "data": "' + base64.b64encode(_PNG) + b'"}'

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: _Response())
    result = RemoteRenderer("https://renderer.example").render(
        RenderRequest(kind="mermaid", source="graph TD; A-->B;")
    )
    assert result.data == _PNG
    assert result.format == "png"


def test_remote_renderer_raises_tool_error_on_error_response(monkeypatch):
    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok": false, "error": "boom"}'

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: _Response())
    try:
        RemoteRenderer("https://renderer.example").render(
            RenderRequest(kind="mermaid", source="graph TD; A-->B;")
        )
    except ToolError as exc:
        assert "boom" in str(exc)
    else:
        raise AssertionError("Expected ToolError")


class FakeRenderer:
    def render(self, request):
        return RenderResult(data=_PNG, format=request.format, renderer=request.kind, duration_ms=1)


def test_render_diagram_can_delegate_without_local_graphviz(monkeypatch):
    import diagrams_mcp.tools.render as render_tool

    monkeypatch.setattr(render_tool, "_graphviz_available", False)
    monkeypatch.setattr(render_tool, "get_renderer", lambda: FakeRenderer())
    result = render_tool.render_diagram("ignored", download_link=False)
    assert result.to_image_content().mimeType == "image/png"


def test_render_mermaid_can_delegate_without_mmdc(monkeypatch):
    import diagrams_mcp.tools.mermaid as mermaid_tool

    monkeypatch.setattr(mermaid_tool, "get_renderer", lambda: FakeRenderer())
    result = mermaid_tool.render_mermaid("graph TD; A-->B;", download_link=False)
    assert result[0].to_image_content().mimeType == "image/png"


def test_render_plantuml_can_delegate_without_java(monkeypatch):
    import diagrams_mcp.tools.plantuml as plantuml_tool

    monkeypatch.setattr(plantuml_tool, "get_renderer", lambda: FakeRenderer())
    result = plantuml_tool.render_plantuml("@startuml\nA -> B\n@enduml", download_link=False)
    assert result.to_image_content().mimeType == "image/png"
