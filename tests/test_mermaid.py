import pytest
from conftest import has_mmdc
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image

from diagrams_mcp.tools.mermaid import render_mermaid


@has_mmdc
def test_render_mermaid_simple():
    """render_mermaid returns an Image for valid Mermaid syntax."""
    definition = "graph TD;\n    A-->B;\n    B-->C;"
    result = render_mermaid(definition=definition)
    assert isinstance(result, Image)
    content = result.to_image_content()
    assert content.mimeType == "image/png"
    assert len(content.data) > 0


@has_mmdc
def test_render_mermaid_invalid_syntax():
    """render_mermaid raises ToolError for invalid Mermaid syntax."""
    with pytest.raises(ToolError, match="Rendering failed"):
        render_mermaid(definition="this is not valid mermaid at all {{{{")


@has_mmdc
def test_render_mermaid_download_link():
    """render_mermaid with download_link=True returns a /images/ path."""
    definition = "graph TD;\n    A-->B;"
    result = render_mermaid(definition=definition, download_link=True)
    assert isinstance(result, str)
    assert result.startswith("/images/")
    token = result.split("/images/")[1]
    assert len(token) == 43


@has_mmdc
def test_render_mermaid_sequence_diagram():
    """render_mermaid handles sequence diagram syntax."""
    definition = """\
sequenceDiagram
    Alice->>Bob: Hello Bob
    Bob-->>Alice: Hi Alice
"""
    result = render_mermaid(definition=definition)
    assert isinstance(result, Image)
