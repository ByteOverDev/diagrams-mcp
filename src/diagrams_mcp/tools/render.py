import shutil
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image

from diagrams_mcp.sandbox import run_code

render = FastMCP("Render")


@render.tool(timeout=30.0)
def render_diagram(code: str, filename: str = "diagram") -> Image:
    """Render a mingrammer/diagrams Python snippet to PNG and return the image.

    The code must be a complete Python script using `from diagrams import ...` imports
    and a `with Diagram(...)` context manager block.

    Args:
        code: Full Python code using the diagrams library.
        filename: Output filename without extension.
    """
    tmpdir = run_code(code, filename=filename)
    try:
        pngs = sorted(Path(tmpdir).glob("*.png"))
        if not pngs:
            raise ToolError(
                "No diagram output produced. Make sure your code uses "
                "a `with Diagram(...):` block."
            )
        return Image(data=pngs[0].read_bytes(), format="png")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
