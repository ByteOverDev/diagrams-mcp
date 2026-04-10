import base64
import json
import zlib

from conftest import has_mmdc
from fastmcp.utilities.types import Image

from diagrams_mcp.tools.mermaid import _detect_type, _mermaid_live_url, render_mermaid


@has_mmdc
def test_render_mermaid_simple():
    """render_mermaid returns [Image, json_metadata] for valid Mermaid syntax."""
    definition = "graph TD;\n    A-->B;\n    B-->C;"
    result = render_mermaid(definition=definition)
    assert isinstance(result, list)
    assert len(result) == 2
    # First element: SVG image
    assert isinstance(result[0], Image)
    content = result[0].to_image_content()
    assert content.mimeType == "image/svg+xml"
    assert len(content.data) > 0
    # Second element: JSON metadata
    meta = json.loads(result[1])
    assert meta["valid"] is True
    assert meta["diagramCode"] == definition
    assert meta["diagramType"] == "graph"
    assert meta["previewLink"].startswith("https://mermaid.live/edit#pako:")


@has_mmdc
def test_render_mermaid_invalid_syntax():
    """render_mermaid returns JSON with valid=false for invalid syntax."""
    definition = "this is not valid mermaid at all {{{{"
    result = render_mermaid(definition=definition)
    assert isinstance(result, list)
    assert len(result) == 1
    meta = json.loads(result[0])
    assert meta["valid"] is False
    assert "error" in meta
    assert meta["previewLink"].startswith("https://mermaid.live/edit#pako:")
    assert meta["diagramCode"] == definition


@has_mmdc
def test_render_mermaid_download_link():
    """render_mermaid with download_link=True returns [link_string, json_metadata]."""
    definition = "graph TD;\n    A-->B;"
    result = render_mermaid(definition=definition, download_link=True)
    assert isinstance(result, list)
    assert len(result) == 2
    # First element: download link string (PNG)
    assert isinstance(result[0], str)
    assert result[0].startswith("/images/")
    token = result[0].split("/images/")[1]
    assert len(token) == 43
    # Second element: JSON metadata
    meta = json.loads(result[1])
    assert meta["valid"] is True
    assert meta["previewLink"].startswith("https://mermaid.live/edit#pako:")


@has_mmdc
def test_render_mermaid_sequence_diagram():
    """render_mermaid handles sequence diagram syntax with correct type detection."""
    definition = """\
sequenceDiagram
    Alice->>Bob: Hello Bob
    Bob-->>Alice: Hi Alice
"""
    result = render_mermaid(definition=definition)
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], Image)
    content = result[0].to_image_content()
    assert content.mimeType == "image/svg+xml"
    meta = json.loads(result[1])
    assert meta["diagramType"] == "sequenceDiagram"
    assert meta["valid"] is True


def test_mermaid_live_url_format():
    """_mermaid_live_url returns a valid mermaid.live edit URL."""
    url = _mermaid_live_url("graph TD;\n    A-->B;")
    assert url.startswith("https://mermaid.live/edit#pako:")


def test_mermaid_live_url_roundtrip():
    """The pako-encoded URL can be decoded back to the original definition."""
    definition = "flowchart LR\n    A --> B --> C"
    url = _mermaid_live_url(definition)
    encoded = url.split("#pako:")[1]
    # Restore base64 padding
    padded = encoded + "=" * (-len(encoded) % 4)
    decompressed = zlib.decompress(base64.urlsafe_b64decode(padded))
    state = json.loads(decompressed)
    assert state["code"] == definition
    assert state["updateDiagram"] is True
    assert json.loads(state["mermaid"]) == {"theme": "default"}


def test_detect_type_flowchart():
    """_detect_type identifies flowchart diagrams."""
    assert _detect_type("flowchart LR\n    A --> B") == "flowchart"


def test_detect_type_sequence():
    """_detect_type identifies sequence diagrams."""
    assert _detect_type("sequenceDiagram\n    Alice->>Bob: Hi") == "sequenceDiagram"


def test_detect_type_graph():
    """_detect_type identifies graph diagrams."""
    assert _detect_type("graph TD;\n    A-->B;") == "graph"


def test_detect_type_unknown():
    """_detect_type returns 'unknown' for unrecognized input."""
    assert _detect_type("not a diagram at all") == "unknown"


def test_detect_type_leading_whitespace():
    """_detect_type handles leading whitespace before the keyword."""
    assert _detect_type("  \n  erDiagram\n    A ||--o{ B : has") == "erDiagram"
