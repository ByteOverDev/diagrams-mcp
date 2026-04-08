import pytest
from fastmcp.exceptions import ToolError

from diagrams_mcp.tools.discovery import list_nodes, list_providers, list_services, search_nodes


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
    assert all(isinstance(r, dict) for r in result)
    # Check known nodes are present
    assert any(r["name"] == "EC2" for r in result)
    assert any(r["name"] == "Lambda" for r in result)
    # Verify import path
    ec2_entry = next(r for r in result if r["name"] == "EC2")
    assert ec2_entry["import"] == "from diagrams.aws.compute import EC2"
    # Verify alias detection
    ecs_entry = next(r for r in result if r["name"] == "ECS")
    assert "alias_of" in ecs_entry
    assert ecs_entry["alias_of"] == "ElasticContainerService"


def test_list_nodes_invalid_service():
    with pytest.raises(ToolError, match="Unknown service"):
        list_nodes("aws", "nonexistent")


def test_search_nodes_finds_redis():
    result = search_nodes("redis")
    assert isinstance(result, list)
    assert len(result) > 0
    assert any(r["node"] == "Redis" for r in result)


def test_search_nodes_case_insensitive():
    lower = search_nodes("redis")
    upper = search_nodes("REDIS")
    mixed = search_nodes("ReDiS")
    # All should find the same nodes
    lower_nodes = {r["node"] for r in lower}
    upper_nodes = {r["node"] for r in upper}
    mixed_nodes = {r["node"] for r in mixed}
    assert lower_nodes == upper_nodes == mixed_nodes
    assert len(lower_nodes) > 0


def test_search_nodes_exact_match_first():
    result = search_nodes("EC2")
    assert len(result) > 1
    # Exact match (case-insensitive) should be first
    assert result[0]["node"] == "EC2"


def test_search_nodes_returns_import_path():
    result = search_nodes("EC2")
    ec2 = next(r for r in result if r["node"] == "EC2")
    assert ec2["import"] == "from diagrams.aws.compute import EC2"
    assert ec2["provider"] == "aws"
    assert ec2["service"] == "compute"


def test_search_nodes_includes_alias_of():
    result = search_nodes("ECS")
    aliases = [r for r in result if "alias_of" in r]
    # ECS is an alias for ElasticContainerService in aws.compute
    ecs_alias = next((r for r in aliases if r["node"] == "ECS" and r["provider"] == "aws"), None)
    assert ecs_alias is not None
    assert ecs_alias["alias_of"] == "ElasticContainerService"


def test_search_nodes_empty_result():
    result = search_nodes("zzzznonexistentnodezzzzz")
    assert result == []


def test_search_nodes_empty_query():
    with pytest.raises(ToolError, match="non-empty"):
        search_nodes("")
