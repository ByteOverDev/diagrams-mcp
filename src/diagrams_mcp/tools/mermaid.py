"""Mermaid diagram rendering tool."""

import os
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.utilities.types import Image

from diagrams_mcp.image_store import image_store
from diagrams_mcp.sandbox import run_cli

mermaid = FastMCP("Mermaid")

_PUPPETEER_CONFIG = os.environ.get("MERMAID_PUPPETEER_CONFIG", "/etc/mermaid/puppeteer-config.json")


@mermaid.tool(timeout=30.0)
def render_mermaid(
    definition: str,
    filename: str = "diagram",
    output_path: str | None = None,
    download_link: bool = False,
) -> Image | str:
    """Render a Mermaid diagram definition to PNG and return the image.

    The definition should be valid Mermaid syntax (e.g. flowchart, sequence,
    class, ER, state, or Gantt diagram).

    Args:
        definition: Mermaid diagram definition text.
        filename: Output filename without extension.
        output_path: Optional directory or file path to save the PNG to.
                     If a directory, saves as <directory>/<filename>.png.
                     If omitted, returns the image inline.
        download_link: If True, store the image on the server and return a
                       temporary download URL path (/images/{token}) instead of
                       the inline image. The link expires after 15 minutes.
                       Ignored when output_path is set.
    """
    cmd = ["mmdc", "-i", "-", "-o", "-", "-e", "png"]
    if os.path.isfile(_PUPPETEER_CONFIG):
        cmd.extend(["-p", _PUPPETEER_CONFIG])

    png_data = run_cli(cmd, input_data=definition.encode())

    if output_path:
        dest = Path(output_path).expanduser().resolve()
        if dest.is_dir():
            dest = dest / f"{filename}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(png_data)
        return f"Diagram saved to {dest}"

    if download_link:
        token = image_store.store(png_data, filename)
        return f"/images/{token}"

    return Image(data=png_data, format="png")
