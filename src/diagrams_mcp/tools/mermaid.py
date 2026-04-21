"""Mermaid diagram rendering tool."""

import base64
import json
import os
import re
import zlib
from typing import Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from diagrams_mcp.image_store import default_download_link, deliver_image
from diagrams_mcp.sandbox import run_cli

mermaid = FastMCP("Mermaid")

_PUPPETEER_CONFIG = os.environ.get("MERMAID_PUPPETEER_CONFIG", "/etc/mermaid/puppeteer-config.json")

_DIAGRAM_TYPES = {
    "flowchart": re.compile(r"^\s*flowchart\b"),
    "graph": re.compile(r"^\s*graph\b"),
    "sequenceDiagram": re.compile(r"^\s*sequenceDiagram\b"),
    "classDiagram": re.compile(r"^\s*classDiagram\b"),
    "erDiagram": re.compile(r"^\s*erDiagram\b"),
    "stateDiagram": re.compile(r"^\s*stateDiagram\b"),
    "gantt": re.compile(r"^\s*gantt\b"),
    "pie": re.compile(r"^\s*pie\b"),
    "gitGraph": re.compile(r"^\s*gitGraph\b"),
    "journey": re.compile(r"^\s*journey\b"),
    "mindmap": re.compile(r"^\s*mindmap\b"),
    "timeline": re.compile(r"^\s*timeline\b"),
    "sankey": re.compile(r"^\s*sankey\b"),
    "xychart": re.compile(r"^\s*xychart\b"),
    "block": re.compile(r"^\s*block\b"),
    "architecture": re.compile(r"^\s*architecture\b"),
    "kanban": re.compile(r"^\s*kanban\b"),
    "packet": re.compile(r"^\s*packet\b"),
    "quadrantChart": re.compile(r"^\s*quadrantChart\b"),
    "C4Context": re.compile(r"^\s*C4Context\b"),
    "C4Container": re.compile(r"^\s*C4Container\b"),
    "C4Component": re.compile(r"^\s*C4Component\b"),
    "C4Dynamic": re.compile(r"^\s*C4Dynamic\b"),
    "C4Deployment": re.compile(r"^\s*C4Deployment\b"),
    "requirementDiagram": re.compile(r"^\s*requirementDiagram\b"),
    "zenuml": re.compile(r"^\s*zenuml\b", re.IGNORECASE),
    "ishikawa": re.compile(r"^\s*ishikawa\b"),
    "radar": re.compile(r"^\s*radar\b"),
    "wardley": re.compile(r"^\s*wardley\b"),
    "venn": re.compile(r"^\s*venn\b"),
}


def _detect_type(definition: str) -> str:
    """Detect the Mermaid diagram type from the first non-empty line of the definition."""
    first_line = ""
    for line in definition.splitlines():
        stripped = line.strip()
        if stripped:
            first_line = stripped
            break
    for name, pattern in _DIAGRAM_TYPES.items():
        if pattern.match(first_line):
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


@mermaid.tool(timeout=30.0, annotations={"readOnlyHint": True})
def render_mermaid(
    definition: str,
    filename: str = "diagram",
    format: Literal["png", "svg", "pdf"] = "png",
    download_link: bool | None = None,
):
    """Render a Mermaid diagram definition and return the image with metadata.

    The definition should be valid Mermaid syntax (e.g. flowchart, sequence,
    class, ER, state, or Gantt diagram).

    Returns a list of content blocks: the rendered image plus a JSON text
    block with metadata including a mermaid.live edit link for opening the
    diagram in a browser editor.

    Args:
        definition: Mermaid diagram definition text.
        filename: Output filename without extension.
        format: Output format — ``"png"`` (default), ``"svg"``, or ``"pdf"``.
        download_link: If True, return a temporary download URL path
                       (/images/{token}) that expires after 15 minutes; if
                       False, return inline image bytes. Defaults to True
                       (URL) — set ``DIAGRAMS_INLINE_DEFAULT=true`` on the
                       server to flip the default. SVG/PDF and PNGs larger
                       than the inline limit always use a download link.
    """
    if download_link is None:
        download_link = default_download_link()
    preview_link = _mermaid_live_url(definition)
    diagram_type = _detect_type(definition)

    cmd = ["mmdc", "-i", "-", "-o", "-", "-e", format]
    if os.path.isfile(_PUPPETEER_CONFIG):
        cmd.extend(["-p", _PUPPETEER_CONFIG])

    try:
        image_data = run_cli(cmd, input_data=definition.encode())
        image_result = deliver_image(image_data, filename, download_link, fmt=format)
        metadata = {
            "diagramType": diagram_type,
            "valid": True,
            "previewLink": preview_link,
        }
        return [image_result, json.dumps(metadata)]
    except ToolError as exc:
        metadata = {
            "diagramType": diagram_type,
            "valid": False,
            "error": str(exc),
            "previewLink": preview_link,
        }
        return [json.dumps(metadata)]
