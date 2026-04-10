"""Mermaid diagram rendering tool."""

import base64
import json
import os
import re
import zlib

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from diagrams_mcp.image_store import deliver_image
from diagrams_mcp.sandbox import run_cli

mermaid = FastMCP("Mermaid")

_PUPPETEER_CONFIG = os.environ.get("MERMAID_PUPPETEER_CONFIG", "/etc/mermaid/puppeteer-config.json")

_DIAGRAM_TYPES = {
    "flowchart": re.compile(r"^\s*flowchart", re.MULTILINE),
    "graph": re.compile(r"^\s*graph\s", re.MULTILINE),
    "sequenceDiagram": re.compile(r"^\s*sequenceDiagram", re.MULTILINE),
    "classDiagram": re.compile(r"^\s*classDiagram", re.MULTILINE),
    "erDiagram": re.compile(r"^\s*erDiagram", re.MULTILINE),
    "stateDiagram": re.compile(r"^\s*stateDiagram", re.MULTILINE),
    "gantt": re.compile(r"^\s*gantt", re.MULTILINE),
    "pie": re.compile(r"^\s*pie", re.MULTILINE),
    "gitGraph": re.compile(r"^\s*gitGraph", re.MULTILINE),
    "journey": re.compile(r"^\s*journey", re.MULTILINE),
    "mindmap": re.compile(r"^\s*mindmap", re.MULTILINE),
    "timeline": re.compile(r"^\s*timeline", re.MULTILINE),
    "sankey": re.compile(r"^\s*sankey", re.MULTILINE),
    "xychart": re.compile(r"^\s*xychart", re.MULTILINE),
    "block": re.compile(r"^\s*block", re.MULTILINE),
    "architecture": re.compile(r"^\s*architecture", re.MULTILINE),
    "kanban": re.compile(r"^\s*kanban", re.MULTILINE),
    "packet": re.compile(r"^\s*packet", re.MULTILINE),
    "quadrantChart": re.compile(r"^\s*quadrantChart", re.MULTILINE),
}


def _detect_type(definition: str) -> str:
    """Detect the Mermaid diagram type from the first keyword in the definition."""
    for name, pattern in _DIAGRAM_TYPES.items():
        if pattern.search(definition):
            return name
    return "unknown"


def _mermaid_live_url(code: str) -> str:
    """Generate a mermaid.live edit URL for the given diagram definition.

    Uses pako-compatible encoding: JSON state -> zlib compress -> base64url.
    No external API calls or auth required.
    """
    state = {
        "code": code,
        "mermaid": json.dumps({"theme": "default"}),
        "updateDiagram": True,
        "rough": False,
    }
    json_bytes = json.dumps(state).encode("utf-8")
    compressed = zlib.compress(json_bytes, level=9)
    encoded = base64.urlsafe_b64encode(compressed).decode().rstrip("=")
    return f"https://mermaid.live/edit#pako:{encoded}"


@mermaid.tool(timeout=30.0)
def render_mermaid(
    definition: str,
    filename: str = "diagram",
    download_link: bool = False,
) -> list:
    """Render a Mermaid diagram definition and return the image with metadata.

    The definition should be valid Mermaid syntax (e.g. flowchart, sequence,
    class, ER, state, or Gantt diagram).

    Returns a list of content blocks: the rendered image (SVG inline or PNG
    download link) plus a JSON text block with metadata including a
    mermaid.live edit link for opening the diagram in a browser editor.

    Args:
        definition: Mermaid diagram definition text.
        filename: Output filename without extension.
        download_link: If True, store the image on the server and return a
                       temporary download URL path (/images/{token}) instead of
                       the inline image. The link expires after 15 minutes.
    """
    preview_link = _mermaid_live_url(definition)
    diagram_type = _detect_type(definition)

    fmt = "png" if download_link else "svg"
    cmd = ["mmdc", "-i", "-", "-o", "-", "-e", fmt]
    if os.path.isfile(_PUPPETEER_CONFIG):
        cmd.extend(["-p", _PUPPETEER_CONFIG])

    try:
        image_data = run_cli(cmd, input_data=definition.encode())
        image_fmt = "png" if download_link else "svg+xml"
        image_result = deliver_image(image_data, filename, download_link, fmt=image_fmt)
        metadata = {
            "diagramCode": definition,
            "diagramType": diagram_type,
            "valid": True,
            "previewLink": preview_link,
        }
        return [image_result, json.dumps(metadata)]
    except ToolError as exc:
        metadata = {
            "diagramCode": definition,
            "diagramType": diagram_type,
            "valid": False,
            "error": str(exc),
            "previewLink": preview_link,
        }
        return [json.dumps(metadata)]
