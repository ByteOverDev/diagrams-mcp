"""PlantUML diagram rendering tool."""

import os
from typing import Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import File, Image

from diagrams_mcp.image_store import default_download_link, deliver_image
from diagrams_mcp.sandbox import run_cli

plantuml = FastMCP("PlantUML")

_PLANTUML_JAR = os.environ.get("PLANTUML_JAR", "/opt/plantuml.jar")


@plantuml.tool(timeout=30.0, annotations={"readOnlyHint": True})
def render_plantuml(
    definition: str,
    filename: str = "diagram",
    format: Literal["png", "svg", "pdf"] = "png",
    download_link: bool | None = None,
) -> Image | File | str:
    """Render a PlantUML diagram definition and return the image.

    The definition should be valid PlantUML syntax wrapped in @startuml/@enduml
    (sequence, class, component, activity, state, deployment, etc.).

    Args:
        definition: PlantUML diagram definition text.
        filename: Output filename without extension.
        format: Output format — ``"png"`` (default) or ``"svg"``.
                PDF is not supported (requires Batik/FOP).
        download_link: If True, return a temporary download URL path
                       (/images/{token}) that expires after 15 minutes; if
                       False, return inline image bytes. Defaults to True
                       (URL) — set ``DIAGRAMS_INLINE_DEFAULT=true`` on the
                       server to flip the default. SVG and PNGs larger than
                       the inline limit always use a download link.
    """
    if format == "pdf":
        raise ToolError(
            "PDF output is not supported for PlantUML (requires Batik/FOP). Use png or svg."
        )
    if download_link is None:
        download_link = default_download_link()

    data = run_cli(
        [
            "java",
            "-Djava.awt.headless=true",
            "-Xmx256m",
            "-DPLANTUML_SECURITY_PROFILE=SANDBOX",
            "-jar",
            _PLANTUML_JAR,
            f"-t{format}",
            "-pipe",
        ],
        input_data=definition.encode(),
    )
    return deliver_image(data, filename, download_link, fmt=format)
