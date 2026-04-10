import importlib

import pytest
from fastmcp.exceptions import ToolError

from diagrams_mcp.tools.equivalence import CATEGORIES, find_equivalent, list_categories


# ---------------------------------------------------------------------------
# find_equivalent — happy paths
# ---------------------------------------------------------------------------
def test_find_equivalent_ec2_to_gcp():
    """Look up EC2 with target gcp — should find ComputeEngine."""
    result = find_equivalent("EC2", target_provider="gcp")
    assert result["category"] == "virtual_machine"
    assert result["description"] == "Virtual machine / compute instance"
    assert result["source"]["node"] == "EC2"
    assert result["source"]["provider"] == "aws"
    assert any(
        e["node"] == "ComputeEngine" and e["provider"] == "gcp"
        for e in result["equivalents"]
    )


def test_find_equivalent_alias_lookup():
    """Alias 'EKS' should resolve to container_orchestration."""
    result = find_equivalent("EKS")
    assert result["category"] == "container_orchestration"
    assert result["source"]["provider"] == "aws"
    # Source must not leak into equivalents when queried via alias.
    assert not any(e["provider"] == "aws" for e in result["equivalents"])


def test_find_equivalent_no_target_returns_all():
    """Omitting target_provider returns equivalents from all other providers."""
    result = find_equivalent("EC2")
    providers = {e["provider"] for e in result["equivalents"]}
    # EC2 is aws — equivalents should include gcp and azure
    assert "gcp" in providers
    assert "azure" in providers


def test_find_equivalent_ambiguous_multi_provider():
    """APIGateway exists in both aws and gcp — should raise, not silently pick one."""
    with pytest.raises(ToolError, match="Ambiguous.*APIGateway.*providers"):
        find_equivalent("APIGateway")


def test_find_equivalent_ambiguous_multi_category():
    """PubSub appears in message_queue and notification_service — should raise."""
    with pytest.raises(ToolError, match="Ambiguous.*PubSub.*categories"):
        find_equivalent("PubSub")


def test_find_equivalent_case_insensitive():
    """Lookups are case-insensitive."""
    lower = find_equivalent("ec2", target_provider="gcp")
    upper = find_equivalent("EC2", target_provider="gcp")
    assert lower["category"] == upper["category"]
    assert lower["source"]["node"] == "EC2"
    assert lower["source"]["provider"] == "aws"
    assert any(
        e["node"] == "ComputeEngine" and e["provider"] == "gcp"
        for e in lower["equivalents"]
    )


def test_find_equivalent_return_schema():
    """Verify the return dict has the expected top-level keys and nested structure."""
    result = find_equivalent("Lambda")
    assert set(result.keys()) == {"category", "description", "source", "equivalents"}
    # Source entry
    assert "node" in result["source"]
    assert "provider" in result["source"]
    assert "service" in result["source"]
    assert "import" in result["source"]
    # Equivalents entries
    for eq in result["equivalents"]:
        assert "node" in eq
        assert "provider" in eq
        assert "service" in eq
        assert "import" in eq


# ---------------------------------------------------------------------------
# find_equivalent — error cases
# ---------------------------------------------------------------------------
def test_find_equivalent_unknown_node():
    with pytest.raises(ToolError, match="No equivalence mapping"):
        find_equivalent("NonexistentNode123")


def test_find_equivalent_empty_node():
    with pytest.raises(ToolError, match="non-empty"):
        find_equivalent("")


def test_find_equivalent_whitespace_node():
    with pytest.raises(ToolError, match="non-empty"):
        find_equivalent("   ")


def test_find_equivalent_unknown_provider():
    with pytest.raises(ToolError, match="Unknown provider"):
        find_equivalent("EC2", target_provider="nonexistent")


# ---------------------------------------------------------------------------
# list_categories
# ---------------------------------------------------------------------------
def test_list_categories_structure():
    """Each category has category, description, providers, nodes keys."""
    result = list_categories()
    assert isinstance(result, list)
    for cat in result:
        assert set(cat.keys()) == {"category", "description", "providers", "nodes"}
        assert isinstance(cat["providers"], list)
        assert isinstance(cat["nodes"], dict)


def test_list_categories_coverage():
    """list_categories returns exactly one entry per CATEGORIES key."""
    result = list_categories()
    assert len(result) == len(CATEGORIES)


def test_list_categories_includes_known_categories():
    """Spot-check that well-known categories exist."""
    result = list_categories()
    names = {c["category"] for c in result}
    assert "virtual_machine" in names
    assert "object_storage" in names
    assert "load_balancer" in names
    assert "relational_database" in names


# ---------------------------------------------------------------------------
# Data integrity: all CATEGORIES nodes must exist in the diagrams package
# ---------------------------------------------------------------------------
def _collect_category_nodes():
    """Yield (category, provider, service, node) for every entry in CATEGORIES."""
    for cat_name, cat_data in CATEGORIES.items():
        for provider, nodes in cat_data["providers"].items():
            for entry in nodes:
                yield cat_name, provider, entry["service"], entry["node"]


@pytest.mark.parametrize(
    "cat,provider,service,node",
    list(_collect_category_nodes()),
    ids=[f"{c}/{p}/{s}/{n}" for c, p, s, n in _collect_category_nodes()],
)
def test_category_node_importable(cat, provider, service, node):
    """Every node in CATEGORIES must be importable from the diagrams package."""
    mod = importlib.import_module(f"diagrams.{provider}.{service}")
    assert hasattr(mod, node), (
        f"Node {node!r} not found in diagrams.{provider}.{service} "
        f"(category: {cat})"
    )
