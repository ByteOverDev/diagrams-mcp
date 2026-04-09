"""PlantUML diagram rendering tool."""

import os

from fastmcp import FastMCP
from fastmcp.utilities.types import Image

from diagrams_mcp.image_store import deliver_image
from diagrams_mcp.sandbox import run_cli

plantuml = FastMCP("PlantUML")

_PLANTUML_JAR = os.environ.get("PLANTUML_JAR", "/opt/plantuml.jar")


@plantuml.tool(timeout=30.0)
def render_plantuml(
    definition: str,
    filename: str = "diagram",
    output_path: str | None = None,
    download_link: bool = False,
) -> Image | str:
    """Render a PlantUML diagram definition to PNG and return the image.

    The definition should be valid PlantUML syntax wrapped in @startuml/@enduml
    (sequence, class, component, activity, state, deployment, etc.).

    Args:
        definition: PlantUML diagram definition text.
        filename: Output filename without extension.
        output_path: Optional directory or file path to save the PNG to.
                     If a directory, saves as <directory>/<filename>.png.
                     If omitted, returns the image inline.
        download_link: If True, store the image on the server and return a
                       temporary download URL path (/images/{token}) instead of
                       the inline image. The link expires after 15 minutes.
                       Ignored when output_path is set.
    """
    png_data = run_cli(
        [
            "java",
            "-Djava.awt.headless=true",
            "-DPLANTUML_SECURITY_PROFILE=SANDBOX",
            "-jar",
            _PLANTUML_JAR,
            "-tpng",
            "-pipe",
        ],
        input_data=definition.encode(),
    )
    return deliver_image(png_data, filename, output_path, download_link)
