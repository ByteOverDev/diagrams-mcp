from fastmcp import FastMCP

from diagrams_mcp.tools.discovery import discovery
from diagrams_mcp.tools.render import render

mcp = FastMCP(
    "diagrams",
    instructions=(
        "Generate cloud architecture diagrams using Python's mingrammer/diagrams library. "
        "Use search_nodes to find components by keyword (returns import paths), or browse with "
        "list_providers -> list_services -> list_nodes. Then render_diagram to produce PNG images."
    ),
    mask_error_details=True,
)

mcp.mount(render)
mcp.mount(discovery)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
