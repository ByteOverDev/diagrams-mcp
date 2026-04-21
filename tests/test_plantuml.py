import pytest
from conftest import has_plantuml
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image

from diagrams_mcp.tools.plantuml import render_plantuml


@has_plantuml
def test_render_plantuml_simple():
    """render_plantuml returns an Image when inline is explicitly requested."""
    definition = "@startuml\nAlice -> Bob: Hello\n@enduml"
    result = render_plantuml(definition=definition, download_link=False)
    assert isinstance(result, Image)
    content = result.to_image_content()
    assert content.mimeType == "image/png"
    assert len(content.data) > 0


@has_plantuml
def test_render_plantuml_invalid_syntax():
    """render_plantuml raises ToolError for invalid PlantUML syntax."""
    with pytest.raises(ToolError, match="Rendering failed"):
        render_plantuml(definition="this is definitely not plantuml")


@has_plantuml
def test_render_plantuml_download_link():
    """render_plantuml with download_link=True returns a /images/ path."""
    definition = "@startuml\nAlice -> Bob: Hello\n@enduml"
    result = render_plantuml(definition=definition, download_link=True)
    assert isinstance(result, str)
    assert result.startswith("/images/")
    token = result.split("/images/")[1]
    assert len(token) == 43


@has_plantuml
def test_render_plantuml_class_diagram():
    """render_plantuml handles class diagram syntax."""
    definition = """\
@startuml
class Car {
  +String make
  +String model
  +start()
}
@enduml
"""
    result = render_plantuml(definition=definition, download_link=False)
    assert isinstance(result, Image)


@has_plantuml
def test_render_plantuml_svg_always_returns_download_link():
    """SVG always auto-promotes to a download link regardless of download_link arg."""
    definition = "@startuml\nAlice -> Bob: Hello\n@enduml"
    result = render_plantuml(definition=definition, format="svg", download_link=False)
    assert isinstance(result, str)
    assert "/images/" in result


def test_render_plantuml_pdf_rejected():
    """render_plantuml raises ToolError when format='pdf' is requested."""
    definition = "@startuml\nAlice -> Bob: Hello\n@enduml"
    with pytest.raises(ToolError, match="PDF output is not supported for PlantUML"):
        render_plantuml(definition=definition, format="pdf")
