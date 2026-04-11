import re
import shutil
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image

from diagrams_mcp.image_store import deliver_image
from diagrams_mcp.sandbox import run_code
from diagrams_mcp.tools.discovery import _get_node_index

render = FastMCP("Render")

_graphviz_available = shutil.which("dot") is not None

_GRAPHVIZ_MISSING_MSG = (
    "Graphviz is not installed. The render_diagram tool requires it.\n"
    "Install with: brew install graphviz (macOS) or apt install graphviz (Linux)"
)

_RE_MODULE_NOT_FOUND = re.compile(
    r"ModuleNotFoundError: No module named 'diagrams\.(\w+)\.(\w+)'"
)
_RE_IMPORT_ERROR = re.compile(
    r"ImportError: cannot import name '(\w+)' from 'diagrams\.(\w+)\.(\w+)'"
)


def _enhance_import_error(message: str) -> str:
    """Detect import errors in ToolError messages and append suggestions."""
    # Case 1: Bad service module (e.g., diagrams.aws.nonexistent)
    m = _RE_MODULE_NOT_FOUND.search(message)
    if m:
        provider, bad_service = m.group(1), m.group(2)
        index = _get_node_index()
        services = sorted({e["service"] for e in index if e["provider"] == provider})
        if services:
            suggestion = (
                f"\n\nNo service '{bad_service}' in provider '{provider}'."
                f"\nAvailable services: {', '.join(services)}"
            )
            return message + suggestion
        return message

    # Case 2: Bad node class (e.g., NonexistentNode from diagrams.aws.compute)
    m = _RE_IMPORT_ERROR.search(message)
    if m:
        bad_node, provider, service = m.group(1), m.group(2), m.group(3)
        index = _get_node_index()
        nodes = sorted(
            e["node"] for e in index if e["provider"] == provider and e["service"] == service
        )
        if nodes:
            # Show up to 20 node names to keep the message manageable
            display = nodes[:20]
            suffix = f" ... and {len(nodes) - 20} more" if len(nodes) > 20 else ""
            suggestion = (
                f"\n\nNo node '{bad_node}' in '{provider}.{service}'."
                f"\nAvailable nodes: {', '.join(display)}{suffix}"
            )
            return message + suggestion
        return message

    return message


@render.tool(timeout=30.0)
def render_diagram(
    code: str,
    filename: str = "diagram",
    download_link: bool = False,
) -> Image | str:
    """Render a mingrammer/diagrams Python snippet to PNG and return the image.

    The code must be a complete Python script using `from diagrams import ...` imports
    and a `with Diagram(...)` context manager block.

    Args:
        code: Full Python code using the diagrams library.
        filename: Output filename without extension.
        download_link: If True, store the image on the server and return a
                       temporary download URL path (/images/{token}) instead of
                       the inline image. The link expires after 15 minutes.
    """
    if not _graphviz_available:
        raise ToolError(_GRAPHVIZ_MISSING_MSG)
    try:
        tmpdir = run_code(code, filename=filename)
    except ToolError as exc:
        raise ToolError(_enhance_import_error(str(exc))) from exc
    try:
        pngs = sorted(Path(tmpdir).glob("*.png"))
        if not pngs:
            raise ToolError(
                "No diagram output produced. Make sure your code uses a `with Diagram(...):` block."
            )
        png_data = pngs[0].read_bytes()
        return deliver_image(png_data, filename, download_link)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
