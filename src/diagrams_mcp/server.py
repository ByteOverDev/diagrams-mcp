from fastmcp import FastMCP

from diagrams_mcp.tools.discovery import discovery
from diagrams_mcp.tools.render import render

mcp = FastMCP(
    "diagrams",
    instructions=(
        "Generate cloud architecture diagrams using Python's mingrammer/diagrams library. "
        "Use list_providers, list_services, and list_nodes to discover available components, "
        "then render_diagram to produce PNG images from diagrams code."
    ),
    mask_error_details=True,
)

mcp.mount(render)
mcp.mount(discovery)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
