import pytest
from conftest import has_plantuml
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image

from diagrams_mcp.tools.plantuml import render_plantuml


@has_plantuml
def test_render_plantuml_simple():
    """render_plantuml returns an Image for valid PlantUML syntax."""
    definition = "@startuml\nAlice -> Bob: Hello\n@enduml"
    result = render_plantuml(definition=definition)
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
    result = render_plantuml(definition=definition)
    assert isinstance(result, Image)
