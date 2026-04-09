import pytest
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image

from diagrams_mcp.tools.render import render_diagram


def test_render_simple_diagram():
    """render_diagram returns an Image for a valid diagram."""
    code = """\
from diagrams import Diagram
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS

with Diagram("Test"):
    EC2("web") >> RDS("db")
"""
    result = render_diagram(code=code)
    assert isinstance(result, Image)
    content = result.to_image_content()
    assert content.mimeType == "image/png"
    assert len(content.data) > 0


def test_render_invalid_code():
    """render_diagram raises ToolError for code with syntax errors."""
    with pytest.raises(ToolError, match="Diagram code failed"):
        render_diagram(code="def f(")


def test_render_no_diagram_output():
    """render_diagram raises ToolError when code produces no PNG."""
    with pytest.raises(ToolError, match="No diagram output produced"):
        render_diagram(code="print('hello')")


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


def test_render_default_returns_image():
    """render_diagram without download_link still returns an Image."""
    code = """\
from diagrams import Diagram
from diagrams.aws.compute import EC2

with Diagram("Test"):
    EC2("web")
"""
    result = render_diagram(code=code)
    assert isinstance(result, Image)
