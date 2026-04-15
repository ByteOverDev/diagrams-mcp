import base64
import re
import shutil
import site
import sys
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import File, Image

from diagrams_mcp.image_store import deliver_image
from diagrams_mcp.sandbox import run_code
from diagrams_mcp.tools.discovery import _get_node_index

render = FastMCP("Render")

_graphviz_available = shutil.which("dot") is not None


def _graphviz_install_hint() -> str:
    if sys.platform == "darwin":
        return "Install with: brew install graphviz"
    if sys.platform == "win32":
        return (
            "Install with: choco install graphviz  or download from https://graphviz.org/download/"
        )
    # Linux and other Unix-like
    return "Install with: apt install graphviz (Debian/Ubuntu) or dnf install graphviz (Fedora)"


def _find_resources_dir() -> Path | None:
    """Locate the diagrams 'resources' directory in site-packages."""
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        candidate = Path(sp) / "resources"
        if candidate.is_dir():
            return candidate
    return None


_RESOURCES_DIR = _find_resources_dir()

_RE_SVG_IMAGE_HREF = re.compile(r'(<image\b[^>]*?xlink:href=")([^"]+\.png)(")')


def _embed_svg_images(svg_data: bytes) -> bytes:
    """Replace local file-path image references in SVG with inline base64 data URIs."""
    if _RESOURCES_DIR is None:
        return svg_data

    svg_text = svg_data.decode("utf-8")
    resources_suffix = "/resources/"

    def _replace_href(match: re.Match) -> str:
        prefix, href, suffix = match.group(1), match.group(2), match.group(3)
        # Extract the relative path after "resources/"
        idx = href.find(resources_suffix)
        if idx == -1:
            return match.group(0)
        rel_path = href[idx + len(resources_suffix) :]
        try:
            candidate = (_RESOURCES_DIR / rel_path).resolve()
            if not candidate.is_relative_to(_RESOURCES_DIR.resolve()):
                return match.group(0)
            if not candidate.is_file():
                return match.group(0)
            b64 = base64.b64encode(candidate.read_bytes()).decode("ascii")
        except (OSError, ValueError):
            return match.group(0)
        return f"{prefix}data:image/png;base64,{b64}{suffix}"

    result = _RE_SVG_IMAGE_HREF.sub(_replace_href, svg_text)
    return result.encode("utf-8")


_GRAPHVIZ_MISSING_MSG = (
    "Graphviz is not installed. The render_diagram tool requires it.\n" + _graphviz_install_hint()
)

_RE_MODULE_NOT_FOUND = re.compile(
    r"ModuleNotFoundError: No module named 'diagrams\.(\w+)(?:\.(\w+))?'"
)
_RE_IMPORT_ERROR = re.compile(
    r"ImportError: cannot import name '(\w+)' from 'diagrams\.(\w+)\.(\w+)'"
)


def _enhance_import_error(message: str) -> str:
    """Detect import errors in ToolError messages and append suggestions."""
    # Case 1a: Bad provider (e.g., diagrams.nonexistent)
    # Case 1b: Bad service module (e.g., diagrams.aws.nonexistent)
    m = _RE_MODULE_NOT_FOUND.search(message)
    if m:
        provider, bad_service = m.group(1), m.group(2)
        index = _get_node_index()
        if bad_service is None:
            # Bad provider — suggest available providers
            providers = sorted({e["provider"] for e in index})
            if providers:
                suggestion = (
                    f"\n\nNo provider '{provider}' in diagrams."
                    f"\nAvailable providers: {', '.join(providers)}"
                )
                return message + suggestion
        else:
            # Bad service within a known provider
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


@render.tool(timeout=30.0, annotations={"readOnlyHint": True})
def render_diagram(
    code: str,
    filename: str = "diagram",
    format: Literal["png", "svg", "pdf"] = "png",
    download_link: bool = False,
) -> Image | File | str:
    """Render a mingrammer/diagrams Python snippet to PNG and return the image.

    The code must be a complete Python script using `from diagrams import ...` imports
    and a `with Diagram(...)` context manager block.

    Use search_nodes to verify node names and get correct import paths before writing code.
    Read the diagrams://reference/diagram, diagrams://reference/edge, and
    diagrams://reference/cluster resources for constructor options and usage examples.

    Args:
        code: Full Python code using the diagrams library.
        filename: Output filename without extension.
        format: Output format — ``"png"`` (default), ``"svg"``, or ``"pdf"``.
        download_link: If True, store the image on the server and return a
                       temporary download URL path (/images/{token}) instead of
                       the inline image. The link expires after 15 minutes.
    """
    if not _graphviz_available:
        raise ToolError(_GRAPHVIZ_MISSING_MSG)
    try:
        tmpdir = run_code(code, filename=filename, outformat=format)
    except ToolError as exc:
        raise ToolError(_enhance_import_error(str(exc))) from exc
    try:
        outputs = sorted(Path(tmpdir).glob(f"*.{format}"))
        if not outputs:
            raise ToolError(
                "No diagram output produced. Make sure your code uses a `with Diagram(...):` block."
            )
        data = outputs[0].read_bytes()
        if format == "svg":
            try:
                data = _embed_svg_images(data)
            except (UnicodeDecodeError, OSError) as exc:
                raise ToolError(f"Failed to embed SVG images: {exc}") from exc
        return deliver_image(data, filename, download_link, fmt=format)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
