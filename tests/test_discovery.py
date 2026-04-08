import pytest
from fastmcp.exceptions import ToolError

from diagrams_mcp.tools.discovery import list_nodes, list_providers, list_services


def test_list_providers():
    result = list_providers()
    assert isinstance(result, list)
    assert "aws" in result
    assert "gcp" in result
    assert "k8s" in result


def test_list_services():
    result = list_services("aws")
    assert isinstance(result, list)
    assert "compute" in result
    assert "database" in result


def test_list_services_invalid_provider():
    with pytest.raises(ToolError, match="Unknown provider"):
        list_services("nonexistent")


def test_list_nodes():
    result = list_nodes("aws", "compute")
    assert isinstance(result, list)
    assert "EC2" in result
    assert "Lambda" in result


def test_list_nodes_invalid_service():
    with pytest.raises(ToolError, match="Unknown service"):
        list_nodes("aws", "nonexistent")
