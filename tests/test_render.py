from unittest.mock import patch

import pytest
from conftest import has_graphviz
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image

from diagrams_mcp.tools.render import render_diagram


def test_render_missing_graphviz():
    """render_diagram raises ToolError with install instructions when Graphviz is missing."""
    with patch("diagrams_mcp.tools.render._graphviz_available", False):
        with pytest.raises(ToolError, match="Graphviz is not installed"):
            render_diagram(code="print('hello')")


@pytest.mark.parametrize(
    "platform,expected",
    [
        ("darwin", "brew install graphviz"),
        ("linux", "apt install graphviz"),
        ("win32", "choco install graphviz"),
    ],
)
def test_graphviz_install_hint_per_platform(platform, expected):
    """_graphviz_install_hint returns platform-appropriate instructions."""
    from diagrams_mcp.tools.render import _graphviz_install_hint

    with patch("diagrams_mcp.tools.render.sys") as mock_sys:
        mock_sys.platform = platform
        assert expected in _graphviz_install_hint()


@has_graphviz
def test_render_simple_diagram():
    """render_diagram returns an Image when inline is explicitly requested."""
    code = """\
from diagrams import Diagram
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS

with Diagram("Test"):
    EC2("web") >> RDS("db")
"""
    result = render_diagram(code=code, download_link=False)
    assert isinstance(result, Image)
    content = result.to_image_content()
    assert content.mimeType == "image/png"
    assert len(content.data) > 0


@has_graphviz
def test_render_invalid_code():
    """render_diagram raises ToolError for code with syntax errors."""
    with pytest.raises(ToolError, match="Diagram code failed"):
        render_diagram(code="def f(")


@has_graphviz
def test_render_no_diagram_output():
    """render_diagram raises ToolError when code produces no PNG."""
    with pytest.raises(ToolError, match="No diagram output produced"):
        render_diagram(code="print('hello')")


@has_graphviz
def test_render_with_download_link():
    """render_diagram with download_link=True returns a /images/ path."""
    code = """\
from diagrams import Diagram
from diagrams.aws.compute import EC2

with Diagram("Test"):
    EC2("web")
"""
    result = render_diagram(code=code, download_link=True)
    assert isinstance(result, str)
    assert result.startswith("/images/")
    # Token should be 43 chars (secrets.token_urlsafe(32))
    token = result.split("/images/")[1]
    assert len(token) == 43


@has_graphviz
@pytest.mark.parametrize(
    "env_value,expected_type",
    [
        ("", str),          # unset-like → URL default
        ("false", str),     # explicit false → URL default
        ("true", Image),    # explicit true → inline PNG
    ],
)
def test_render_default_respects_inline_env(monkeypatch, env_value, expected_type):
    """Omitted download_link resolves via DIAGRAMS_INLINE_DEFAULT deterministically."""
    monkeypatch.setenv("DIAGRAMS_INLINE_DEFAULT", env_value)
    code = """\
from diagrams import Diagram
from diagrams.aws.compute import EC2

with Diagram("Test"):
    EC2("web")
"""
    result = render_diagram(code=code)
    assert isinstance(result, expected_type)
    if expected_type is str:
        assert "/images/" in result


@has_graphviz
def test_render_invalid_provider_import():
    """render_diagram suggests valid providers for a bad provider import."""
    code = "from diagrams.nonexistent import Foo"
    with pytest.raises(ToolError, match="Available providers") as exc_info:
        render_diagram(code=code)
    msg = str(exc_info.value)
    assert "nonexistent" in msg
    assert "aws" in msg  # 'aws' is a known provider


@has_graphviz
def test_render_invalid_service_import():
    """render_diagram suggests valid services for a bad service import."""
    code = "from diagrams.aws.nonexistent import Foo"
    with pytest.raises(ToolError, match="Available services") as exc_info:
        render_diagram(code=code)
    msg = str(exc_info.value)
    assert "nonexistent" in msg
    assert "compute" in msg  # 'compute' is a known aws service


@has_graphviz
def test_render_invalid_node_import():
    """render_diagram suggests valid nodes for a bad node import."""
    code = "from diagrams.aws.compute import NonexistentNode"
    with pytest.raises(ToolError, match="Available nodes") as exc_info:
        render_diagram(code=code)
    msg = str(exc_info.value)
    assert "NonexistentNode" in msg
    assert "EC2" in msg  # EC2 is a known aws.compute node


@has_graphviz
def test_render_general_error_passthrough():
    """Non-import errors pass through with the original 'Diagram code failed' message."""
    code = "raise ValueError('something went wrong')"
    with pytest.raises(ToolError, match="Diagram code failed") as exc_info:
        render_diagram(code=code)
    assert "ValueError" in str(exc_info.value)
    assert "something went wrong" in str(exc_info.value)


@has_graphviz
def test_render_diagram_svg_always_returns_download_link():
    """SVG is never inline-decodable by Claude, so it always returns a URL."""
    code = """\
from diagrams import Diagram
from diagrams.aws.compute import EC2

with Diagram("Test"):
    EC2("web")
"""
    result = render_diagram(code=code, format="svg", download_link=False)
    assert isinstance(result, str)
    assert "/images/" in result


@has_graphviz
def test_render_diagram_pdf_always_returns_download_link():
    """PDF is not an inline image block; always returns a URL."""
    code = """\
from diagrams import Diagram
from diagrams.aws.compute import EC2

with Diagram("Test"):
    EC2("web")
"""
    result = render_diagram(code=code, format="pdf", download_link=False)
    assert isinstance(result, str)
    assert "/images/" in result


@has_graphviz
def test_render_diagram_svg_download_link():
    """render_diagram with format='svg' and download_link=True returns a download path."""
    code = """\
from diagrams import Diagram
from diagrams.aws.compute import EC2

with Diagram("Test"):
    EC2("web")
"""
    result = render_diagram(code=code, format="svg", download_link=True)
    assert isinstance(result, str)
    assert result.startswith("/images/")
