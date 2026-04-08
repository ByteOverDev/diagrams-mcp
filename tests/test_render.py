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


def test_render_invalid_code():
    """render_diagram raises ToolError for code with syntax errors."""
    with pytest.raises(ToolError, match="Diagram code failed"):
        render_diagram(code="def f(")


def test_render_no_diagram_output():
    """render_diagram raises ToolError when code produces no PNG."""
    with pytest.raises(ToolError, match="No diagram output produced"):
        render_diagram(code="print('hello')")
