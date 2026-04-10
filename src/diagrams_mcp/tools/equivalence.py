from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

equivalence = FastMCP("Equivalence")


def _build_import_path(provider: str, service: str, node: str) -> str:
    """Construct a Python import statement for a diagrams node."""
    return f"from diagrams.{provider}.{service} import {node}"


# ---------------------------------------------------------------------------
# Category definitions
# Each category maps an infrastructure role to equivalent nodes across providers.
# Schema:
#   CATEGORIES[category_name] = {
#       "description": str,
#       "providers": {
#           provider_name: [{"node": str, "service": str}, ...]
#       }
#   }
# ---------------------------------------------------------------------------
CATEGORIES: dict[str, dict] = {
    "virtual_machine": {
        "description": "Virtual machine / compute instance",
        "providers": {
            "aws": [{"node": "EC2", "service": "compute"}],
            "gcp": [{"node": "ComputeEngine", "service": "compute"}],
            "azure": [{"node": "VM", "service": "compute"}],
        },
    },
    "serverless_function": {
        "description": "Serverless / function-as-a-service compute",
        "providers": {
            "aws": [{"node": "Lambda", "service": "compute"}],
            "gcp": [{"node": "Functions", "service": "compute"}],
            "azure": [{"node": "FunctionApps", "service": "compute"}],
        },
    },
    "container_orchestration": {
        "description": "Managed Kubernetes / container orchestration",
        "providers": {
            "aws": [{"node": "ElasticKubernetesService", "service": "compute"}],
            "gcp": [{"node": "KubernetesEngine", "service": "compute"}],
            "azure": [{"node": "KubernetesServices", "service": "compute"}],
        },
    },
    "container_service": {
        "description": "Managed container / serverless container service",
        "providers": {
            "aws": [{"node": "ElasticContainerService", "service": "compute"}],
            "gcp": [{"node": "CloudRun", "service": "compute"}],
            "azure": [{"node": "ContainerInstances", "service": "compute"}],
        },
    },
    "container_registry": {
        "description": "Private container image registry",
        "providers": {
            "aws": [{"node": "EC2ContainerRegistry", "service": "compute"}],
            "gcp": [{"node": "ContainerRegistry", "service": "devtools"}],
            "azure": [{"node": "ContainerRegistries", "service": "compute"}],
        },
    },
    "paas": {
        "description": "Platform-as-a-service / managed application hosting",
        "providers": {
            "aws": [{"node": "ElasticBeanstalk", "service": "compute"}],
            "gcp": [{"node": "AppEngine", "service": "compute"}],
            "azure": [{"node": "AppServices", "service": "compute"}],
        },
    },
    "object_storage": {
        "description": "Object / blob storage service",
        "providers": {
            "aws": [{"node": "SimpleStorageServiceS3", "service": "storage"}],
            "gcp": [{"node": "Storage", "service": "storage"}],
            "azure": [{"node": "BlobStorage", "service": "storage"}],
        },
    },
    "block_storage": {
        "description": "Persistent block storage / disk volumes",
        "providers": {
            "aws": [{"node": "ElasticBlockStoreEBS", "service": "storage"}],
            "gcp": [{"node": "PersistentDisk", "service": "storage"}],
            "azure": [{"node": "Disks", "service": "compute"}],
        },
    },
    "file_storage": {
        "description": "Managed network file system / shared file storage",
        "providers": {
            "aws": [{"node": "ElasticFileSystemEFS", "service": "storage"}],
            "gcp": [{"node": "Filestore", "service": "storage"}],
            "azure": [{"node": "AzureFileshares", "service": "storage"}],
        },
    },
    "relational_database": {
        "description": "Managed relational database service",
        "providers": {
            "aws": [{"node": "RDS", "service": "database"}],
            "gcp": [{"node": "SQL", "service": "database"}],
            "azure": [{"node": "SQLDatabases", "service": "database"}],
        },
    },
    "nosql_database": {
        "description": "Managed NoSQL / document database service",
        "providers": {
            "aws": [{"node": "Dynamodb", "service": "database"}],
            "gcp": [{"node": "Firestore", "service": "database"}],
            "azure": [{"node": "CosmosDb", "service": "database"}],
        },
    },
    "in_memory_cache": {
        "description": "Managed in-memory cache / Redis-compatible service",
        "providers": {
            "aws": [{"node": "ElastiCache", "service": "database"}],
            "gcp": [{"node": "Memorystore", "service": "database"}],
            "azure": [{"node": "CacheForRedis", "service": "database"}],
        },
    },
    "data_warehouse": {
        "description": "Cloud data warehouse / analytics query engine",
        "providers": {
            "aws": [{"node": "Redshift", "service": "analytics"}],
            "gcp": [{"node": "BigQuery", "service": "analytics"}],
            "azure": [{"node": "SynapseAnalytics", "service": "analytics"}],
        },
    },
    "wide_column_database": {
        "description": "Wide-column / sparse table NoSQL database",
        "providers": {
            "aws": [
                {
                    "node": "KeyspacesManagedApacheCassandraService",
                    "service": "database",
                }
            ],
            "gcp": [{"node": "BigTable", "service": "database"}],
            "azure": [{"node": "CosmosDb", "service": "database"}],
        },
    },
    "load_balancer": {
        "description": "Managed load balancing service",
        "providers": {
            "aws": [{"node": "ElasticLoadBalancing", "service": "network"}],
            "gcp": [{"node": "LoadBalancing", "service": "network"}],
            "azure": [{"node": "LoadBalancers", "service": "network"}],
        },
    },
    "cdn": {
        "description": "Content delivery network",
        "providers": {
            "aws": [{"node": "CloudFront", "service": "network"}],
            "gcp": [{"node": "CDN", "service": "network"}],
            "azure": [{"node": "CDNProfiles", "service": "network"}],
        },
    },
    "dns": {
        "description": "Managed DNS service",
        "providers": {
            "aws": [{"node": "Route53", "service": "network"}],
            "gcp": [{"node": "DNS", "service": "network"}],
            "azure": [{"node": "DNSZones", "service": "network"}],
        },
    },
    "vpc": {
        "description": "Virtual private cloud / isolated network",
        "providers": {
            "aws": [{"node": "VPC", "service": "network"}],
            "gcp": [{"node": "VirtualPrivateCloud", "service": "network"}],
            "azure": [{"node": "VirtualNetworks", "service": "network"}],
        },
    },
    "vpn": {
        "description": "VPN gateway / site-to-site VPN service",
        "providers": {
            "aws": [{"node": "VpnGateway", "service": "network"}],
            "gcp": [{"node": "VPN", "service": "network"}],
            "azure": [{"node": "VirtualNetworkGateways", "service": "network"}],
        },
    },
    "api_gateway": {
        "description": "Managed API gateway service",
        "providers": {
            "aws": [{"node": "APIGateway", "service": "network"}],
            "gcp": [{"node": "APIGateway", "service": "api"}],
            "azure": [{"node": "APIManagement", "service": "integration"}],
        },
    },
    "firewall": {
        "description": "Network firewall / packet filtering service",
        "providers": {
            "aws": [{"node": "NetworkFirewall", "service": "network"}],
            "gcp": [{"node": "FirewallRules", "service": "network"}],
            "azure": [{"node": "Firewall", "service": "network"}],
        },
    },
    "iam": {
        "description": "Identity and access management service",
        "providers": {
            "aws": [
                {
                    "node": "IdentityAndAccessManagementIam",
                    "service": "security",
                }
            ],
            "gcp": [{"node": "Iam", "service": "security"}],
            "azure": [
                {"node": "AzureADIdentityProtection", "service": "security"}
            ],
        },
    },
    "kms": {
        "description": "Key management service / encryption key storage",
        "providers": {
            "aws": [{"node": "KeyManagementService", "service": "security"}],
            "gcp": [{"node": "KeyManagementService", "service": "security"}],
            "azure": [{"node": "KeyVaults", "service": "security"}],
        },
    },
    "secret_manager": {
        "description": "Secrets manager / credential vault service",
        "providers": {
            "aws": [{"node": "SecretsManager", "service": "security"}],
            "gcp": [{"node": "SecretManager", "service": "security"}],
            "azure": [{"node": "KeyVaults", "service": "security"}],
        },
    },
    "message_queue": {
        "description": "Managed message queue / pub-sub service",
        "providers": {
            "aws": [{"node": "SimpleQueueServiceSqs", "service": "integration"}],
            "gcp": [{"node": "PubSub", "service": "analytics"}],
            "azure": [{"node": "AzureServiceBus", "service": "integration"}],
        },
    },
    "notification_service": {
        "description": "Push notification / fan-out messaging service",
        "providers": {
            "aws": [
                {"node": "SimpleNotificationServiceSns", "service": "integration"}
            ],
            "gcp": [{"node": "PubSub", "service": "analytics"}],
            "azure": [{"node": "EventGridDomains", "service": "integration"}],
        },
    },
    "stream_processing": {
        "description": "Real-time data stream processing service",
        "providers": {
            "aws": [{"node": "Kinesis", "service": "analytics"}],
            "gcp": [{"node": "Dataflow", "service": "analytics"}],
            "azure": [{"node": "StreamAnalyticsJobs", "service": "analytics"}],
        },
    },
    "etl": {
        "description": "ETL / data pipeline and integration service",
        "providers": {
            "aws": [{"node": "Glue", "service": "analytics"}],
            "gcp": [{"node": "DataFusion", "service": "analytics"}],
            "azure": [{"node": "DataFactories", "service": "analytics"}],
        },
    },
    "ml_platform": {
        "description": "Managed machine learning platform",
        "providers": {
            "aws": [{"node": "Sagemaker", "service": "ml"}],
            "gcp": [{"node": "VertexAI", "service": "ml"}],
            "azure": [
                {
                    "node": "MachineLearningServiceWorkspaces",
                    "service": "ml",
                }
            ],
        },
    },
    "iot_platform": {
        "description": "IoT device management and connectivity platform",
        "providers": {
            "aws": [{"node": "IotCore", "service": "iot"}],
            "gcp": [{"node": "IotCore", "service": "iot"}],
            "azure": [{"node": "IotHub", "service": "iot"}],
        },
    },
}


def _resolve_aliases(provider: str, service: str, node_name: str) -> list[str]:
    """Return package-level alias names that point to the same class as *node_name*.

    For example, ``_resolve_aliases("aws", "compute", "ElasticKubernetesService")``
    returns ``["EKS"]`` because ``diagrams.aws.compute.EKS`` is an alias.
    """
    import importlib

    try:
        mod = importlib.import_module(f"diagrams.{provider}.{service}")
    except ModuleNotFoundError:
        return []
    target = getattr(mod, node_name, None)
    if target is None:
        return []
    return [
        name
        for name in dir(mod)
        if not name.startswith("_") and name != node_name and getattr(mod, name) is target
    ]


def _index_pair(
    index: dict[str, list[tuple[str, str]]], key: str, pair: tuple[str, str]
) -> None:
    """Add *pair* to *index* under *key* if not already present."""
    bucket = index.setdefault(key, [])
    if pair not in bucket:
        bucket.append(pair)


def _index_entry(
    index: dict[str, list[tuple[str, str]]],
    cat_name: str,
    provider: str,
    entry: dict,
) -> None:
    """Index a single CATEGORIES entry (canonical name + aliases)."""
    pair = (cat_name, provider)
    _index_pair(index, entry["node"].lower(), pair)
    for alias in _resolve_aliases(provider, entry["service"], entry["node"]):
        _index_pair(index, alias.lower(), pair)


def _build_reverse_index() -> dict[str, list[tuple[str, str]]]:
    """Build a case-insensitive node name → ``[(category, provider), ...]`` lookup.

    Indexes both the canonical node names listed in ``CATEGORIES`` and any
    package-level aliases discovered via class identity in the ``diagrams``
    package (e.g. ``EKS`` → ``ElasticKubernetesService``).

    Each entry in the returned list is a ``(category_name, provider)`` tuple so
    that callers can detect and report ambiguous lookups (e.g. ``APIGateway``
    exists in both *aws* and *gcp* within the same category, while ``PubSub``
    appears in two different categories).
    """
    index: dict[str, list[tuple[str, str]]] = {}
    for cat_name, cat_data in CATEGORIES.items():
        for provider, entries in cat_data["providers"].items():
            for entry in entries:
                _index_entry(index, cat_name, provider, entry)
    return index


_REVERSE_INDEX: dict[str, list[tuple[str, str]]] = _build_reverse_index()

# Collect valid provider names from CATEGORIES for validation.
_KNOWN_PROVIDERS: set[str] = {
    provider
    for cat_data in CATEGORIES.values()
    for provider in cat_data["providers"]
}


def _resolve_source_entry(
    cat_data: dict, source_provider: str, node_lower: str
) -> dict | None:
    """Find the CATEGORIES entry matching *node_lower* (canonical or alias)."""
    for entry in cat_data["providers"][source_provider]:
        if entry["node"].lower() == node_lower:
            return {
                "node": entry["node"],
                "provider": source_provider,
                "service": entry["service"],
                "import": _build_import_path(
                    source_provider, entry["service"], entry["node"]
                ),
            }
        aliases = _resolve_aliases(source_provider, entry["service"], entry["node"])
        if node_lower in [a.lower() for a in aliases]:
            return {
                "node": entry["node"],
                "provider": source_provider,
                "service": entry["service"],
                "import": _build_import_path(
                    source_provider, entry["service"], entry["node"]
                ),
            }
    return None


def _collect_equivalents(
    cat_data: dict,
    source_provider: str,
    source_entry: dict,
    target_provider: str | None,
) -> list[dict]:
    """Gather equivalent nodes from all providers except the source."""
    equivalents: list[dict] = []
    for provider, entries in cat_data["providers"].items():
        if target_provider is not None and provider != target_provider:
            continue
        for entry in entries:
            is_source = (
                provider == source_provider
                and entry["node"].lower() == source_entry["node"].lower()
            )
            if is_source:
                continue
            equivalents.append(
                {
                    "node": entry["node"],
                    "provider": provider,
                    "service": entry["service"],
                    "import": _build_import_path(
                        provider, entry["service"], entry["node"]
                    ),
                }
            )
    return equivalents


@equivalence.tool
def find_equivalent(node: str, target_provider: str | None = None) -> dict:
    """Find cross-provider equivalents for a diagram node by infrastructure role.

    Given a node name (e.g. 'EC2', 'Lambda', 'ComputeEngine'), returns the
    infrastructure role category it belongs to and the equivalent nodes from
    other providers.

    Args:
        node: Node class name to look up (case-insensitive, e.g. 'EC2', 'lambda').
        target_provider: Optional provider to filter equivalents to
            (e.g. 'gcp', 'azure', 'aws').  If omitted, all equivalents
            across all other providers are returned.

    Returns:
        A dict with keys:
            category (str): Infrastructure role category name.
            description (str): Human-readable description of the category.
            source (dict): The matched node with keys node, provider, service, import.
            equivalents (list[dict]): Equivalent nodes, each with keys
                node, provider, service, import.
    """
    if not node or not node.strip():
        raise ToolError("node must be a non-empty string.")

    if target_provider is not None:
        target_provider = target_provider.strip().lower()
        if target_provider not in _KNOWN_PROVIDERS:
            raise ToolError(
                f"Unknown provider: {target_provider!r}. "
                f"Valid providers: {sorted(_KNOWN_PROVIDERS)}."
            )

    node_lower = node.strip().lower()
    matches = _REVERSE_INDEX.get(node_lower)
    if not matches:
        raise ToolError(
            f"No equivalence mapping found for node {node!r}. "
            "Use list_categories() to see all mapped nodes."
        )

    # Detect ambiguity — multiple distinct categories or multiple providers
    # within the same category — and fail fast so the caller can disambiguate.
    unique_categories = sorted({cat for cat, _prov in matches})
    if len(unique_categories) > 1:
        cat_list = ", ".join(unique_categories)
        raise ToolError(
            f"Ambiguous node {node!r}: exists in multiple categories "
            f"({cat_list}). Use list_categories() to pick the right one "
            f"and look up a provider-specific node instead."
        )

    cat_name = unique_categories[0]
    cat_data = CATEGORIES[cat_name]

    providers_for_node = sorted({prov for _cat, prov in matches})
    if len(providers_for_node) > 1:
        prov_list = ", ".join(providers_for_node)
        raise ToolError(
            f"Ambiguous node {node!r}: exists in providers {prov_list} "
            f"within category {cat_name!r}. Use a provider-specific node "
            f"name instead (see list_categories())."
        )

    # Unambiguous — exactly one (category, provider) pair.
    source_provider = providers_for_node[0]
    source_entry = _resolve_source_entry(cat_data, source_provider, node_lower)
    equivalents = _collect_equivalents(cat_data, source_provider, source_entry, target_provider)

    return {
        "category": cat_name,
        "description": cat_data["description"],
        "source": source_entry,
        "equivalents": equivalents,
    }


@equivalence.tool
def list_categories() -> list[dict]:
    """List all infrastructure role categories with their mapped nodes.

    Returns a list of category dicts, each with:
        category (str): Category identifier (e.g. 'virtual_machine').
        description (str): Human-readable description.
        providers (list[str]): Providers covered by this category.
        nodes (dict): Mapping of provider → list of node names in that category.
    """
    result = []
    for cat_name, cat_data in CATEGORIES.items():
        nodes_by_provider = {
            provider: [entry["node"] for entry in entries]
            for provider, entries in cat_data["providers"].items()
        }
        result.append(
            {
                "category": cat_name,
                "description": cat_data["description"],
                "providers": sorted(cat_data["providers"].keys()),
                "nodes": nodes_by_provider,
            }
        )
    return result
