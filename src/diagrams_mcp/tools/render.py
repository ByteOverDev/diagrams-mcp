import shutil
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image

from diagrams_mcp.image_store import image_store
from diagrams_mcp.sandbox import run_code

render = FastMCP("Render")


@render.tool(timeout=30.0)
def render_diagram(
    code: str,
    filename: str = "diagram",
    output_path: str | None = None,
    download_link: bool = False,
) -> Image | str:
    """Render a mingrammer/diagrams Python snippet to PNG and return the image.

    The code must be a complete Python script using `from diagrams import ...` imports
    and a `with Diagram(...)` context manager block.

    Args:
        code: Full Python code using the diagrams library.
        filename: Output filename without extension.
        output_path: Optional directory or file path to save the PNG to.
                     If a directory, saves as <directory>/<filename>.png.
                     If omitted, returns the image inline.
        download_link: If True, store the image on the server and return a
                       temporary download URL path (/images/{token}) instead of
                       the inline image. The link expires after 15 minutes.
                       Ignored when output_path is set.
    """
    tmpdir = run_code(code, filename=filename)
    try:
        pngs = sorted(Path(tmpdir).glob("*.png"))
        if not pngs:
            raise ToolError(
                "No diagram output produced. Make sure your code uses a `with Diagram(...):` block."
            )
        png_data = pngs[0].read_bytes()

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
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
