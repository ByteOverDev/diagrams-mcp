import base64
import json
import zlib

from conftest import has_mmdc
from fastmcp.utilities.types import Image

from diagrams_mcp.tools.mermaid import _detect_type, _mermaid_live_url, render_mermaid


@has_mmdc
def test_render_mermaid_simple():
    """render_mermaid returns [Image(png), json_metadata] for valid Mermaid syntax."""
    definition = "graph TD;\n    A-->B;\n    B-->C;"
    result = render_mermaid(definition=definition)
    assert isinstance(result, list)
    assert len(result) == 2
    # First element: PNG image (default format)
    assert isinstance(result[0], Image)
    content = result[0].to_image_content()
    assert content.mimeType == "image/png"
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
    assert content.mimeType == "image/png"
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


def test_detect_type_ignores_keyword_on_later_line():
    """_detect_type only checks the first non-empty line, not later lines."""
    # "gantt" appears on a later line as a node name, but the diagram is a graph
    assert _detect_type("graph TD\n    A --> gantt --> B") == "graph"


def test_detect_type_no_substring_match():
    """_detect_type uses word boundaries and does not match keyword substrings."""
    # "sequenceDiagramNode" starts with "sequenceDiagram" but is not a type keyword
    assert _detect_type("sequenceDiagramNode\n    A --> B") == "unknown"


def test_detect_type_c4context():
    """_detect_type identifies C4Context diagrams."""
    assert _detect_type("C4Context\n    Person(user, 'User')") == "C4Context"


def test_detect_type_c4container():
    """_detect_type identifies C4Container diagrams."""
    assert _detect_type("C4Container\n    System(s, 'System')") == "C4Container"


def test_detect_type_c4component():
    """_detect_type identifies C4Component diagrams."""
    assert _detect_type("C4Component\n    Component(c, 'Comp')") == "C4Component"


def test_detect_type_c4dynamic():
    """_detect_type identifies C4Dynamic diagrams."""
    assert _detect_type("C4Dynamic\n    Rel(a, b, 'calls')") == "C4Dynamic"


def test_detect_type_c4deployment():
    """_detect_type identifies C4Deployment diagrams."""
    assert _detect_type("C4Deployment\n    Node(n, 'Server')") == "C4Deployment"


def test_detect_type_requirement_diagram():
    """_detect_type identifies requirementDiagram diagrams."""
    assert _detect_type("requirementDiagram\n    requirement r1 { id: 1 }") == "requirementDiagram"


def test_detect_type_zenuml():
    """_detect_type identifies zenuml diagrams (case-insensitive)."""
    assert _detect_type("zenuml\n    Alice->Bob: hi") == "zenuml"
    assert _detect_type("ZenUML\n    Alice->Bob: hi") == "zenuml"


def test_detect_type_ishikawa_beta():
    """_detect_type identifies ishikawa-beta diagrams."""
    assert _detect_type("ishikawa-beta\n    Problem") == "ishikawa"


def test_detect_type_radar_beta():
    """_detect_type identifies radar-beta diagrams."""
    assert _detect_type("radar-beta\n    axis A, B, C") == "radar"


def test_detect_type_wardley_beta():
    """_detect_type identifies wardley-beta diagrams."""
    assert _detect_type("wardley-beta\n    title My Map") == "wardley"


def test_detect_type_venn_beta():
    """_detect_type identifies venn-beta diagrams."""
    assert _detect_type("venn-beta\n    set A") == "venn"


def test_detect_type_statediagram_v2():
    """_detect_type identifies stateDiagram-v2 variant."""
    assert _detect_type("stateDiagram-v2\n    [*] --> Active") == "stateDiagram"


def test_detect_type_sankey_beta():
    """_detect_type identifies sankey-beta variant."""
    assert _detect_type("sankey-beta\n    A,B,10") == "sankey"


def test_detect_type_xychart_beta():
    """_detect_type identifies xychart-beta variant."""
    assert _detect_type('xychart-beta\n    x-axis "A"') == "xychart"


def test_detect_type_block_beta():
    """_detect_type identifies block-beta variant."""
    assert _detect_type("block-beta\n    columns 3") == "block"


def test_detect_type_packet_beta():
    """_detect_type identifies packet-beta variant."""
    assert _detect_type("packet-beta\n    0-15: Header") == "packet"


@has_mmdc
def test_render_mermaid_svg():
    """render_mermaid with format='svg' returns SVG Image."""
    definition = "graph TD;\n    A-->B;"
    result = render_mermaid(definition=definition, format="svg")
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], Image)
    content = result[0].to_image_content()
    assert content.mimeType == "image/svg+xml"


@has_mmdc
def test_render_mermaid_pdf():
    """render_mermaid with format='pdf' returns PDF File in result list."""
    from fastmcp.utilities.types import File

    definition = "graph TD;\n    A-->B;"
    result = render_mermaid(definition=definition, format="pdf")
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], File)


@has_mmdc
def test_render_mermaid_svg_download_link():
    """render_mermaid with format='svg' and download_link=True returns a download path."""
    definition = "graph TD;\n    A-->B;"
    result = render_mermaid(definition=definition, format="svg", download_link=True)
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], str)
    assert result[0].startswith("/images/")
