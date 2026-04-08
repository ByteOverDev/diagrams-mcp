from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image

render = FastMCP("Render")


@render.tool(timeout=45.0)
def render_diagram(code: str, filename: str = "diagram") -> Image:
    """Render a mingrammer/diagrams Python snippet to PNG and return the image.

    The code must be a complete Python script using `from diagrams import ...` imports
    and a `with Diagram(...)` context manager block.

    Args:
        code: Full Python code using the diagrams library.
        filename: Output filename without extension.
    """
    # TODO: implement sandboxed execution in BYT-118 / BYT-120
    raise ToolError("render_diagram not yet implemented")
