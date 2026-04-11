import asyncio

from diagrams_mcp.prompts import (
    architecture_diagram,
    compare_providers,
    quick_sketch,
    sequence_flow,
)


def test_prompts_registered_on_server():
    from diagrams_mcp.server import mcp

    prompts = asyncio.run(mcp.list_prompts())
    names = {p.name for p in prompts}
    assert "architecture_diagram" in names
    assert "sequence_flow" in names
    assert "compare_providers" in names
    assert "quick_sketch" in names


# --- architecture_diagram ---


def test_architecture_diagram_default():
    text = architecture_diagram()
    assert "search_nodes" in text
    assert "render_diagram" in text
    assert "diagrams://reference/diagram" in text
    assert "list_providers" in text


def test_architecture_diagram_with_provider():
    text = architecture_diagram(provider="aws")
    assert "aws" in text
    assert "search_nodes" in text
    assert "render_diagram" in text
    assert "diagrams://reference/diagram" in text
    # Should not contain the "ask which provider" language
    assert "list_providers" not in text


def test_architecture_diagram_normalizes_provider():
    text = architecture_diagram(provider="AWS")
    # Display text keeps original casing
    assert "**AWS**" in text
    # Tool-call examples use lowercase canonical ID
    assert "list_services('aws')" in text
    assert "list_nodes('aws'" in text


# --- sequence_flow ---


def test_sequence_flow_default():
    text = sequence_flow()
    assert "render_mermaid" in text
    assert "render_plantuml" in text
    assert "diagrams://reference/mermaid" in text
    assert "diagrams://reference/plantuml" in text


def test_sequence_flow_with_mermaid():
    text = sequence_flow(engine="mermaid")
    assert "render_mermaid" in text
    assert "diagrams://reference/mermaid" in text


def test_sequence_flow_with_plantuml():
    text = sequence_flow(engine="plantuml")
    assert "render_plantuml" in text
    assert "diagrams://reference/plantuml" in text


# --- compare_providers ---


def test_compare_providers_default():
    text = compare_providers()
    assert "list_categories" in text
    assert "find_equivalent" in text


def test_compare_providers_with_role():
    text = compare_providers(service_role="virtual_machine")
    assert "find_equivalent" in text
    assert "virtual_machine" in text
    # Should not contain the "browse categories" step
    assert "list_categories" not in text


# --- quick_sketch ---


def test_quick_sketch_default():
    text = quick_sketch()
    assert "render_diagram" in text
    assert "render_mermaid" in text
    assert "render_plantuml" in text


def test_quick_sketch_with_description():
    text = quick_sketch(description="AWS Lambda processing pipeline")
    assert "AWS Lambda processing pipeline" in text
    assert "render_diagram" in text
    assert "render_mermaid" in text
    assert "render_plantuml" in text
