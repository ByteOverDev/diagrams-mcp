import importlib
import pkgutil

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

discovery = FastMCP("Discovery")


def _build_import_path(provider: str, service: str, node: str) -> str:
    """Construct a Python import statement for a diagrams node."""
    return f"from diagrams.{provider}.{service} import {node}"


def _group_node_names(mod: object) -> list[tuple[str, str | None]]:
    """Group public Node subclasses by class identity and detect aliases.

    Returns a list of (name, canonical_or_none) tuples where canonical_or_none
    is None for canonical names and the canonical name string for aliases.
    """
    from diagrams import Node

    class_to_names: dict[int, list[str]] = {}
    for name in dir(mod):
        if name.startswith("_"):
            continue
        obj = getattr(mod, name)
        if isinstance(obj, type) and issubclass(obj, Node):
            class_to_names.setdefault(id(obj), []).append(name)

    results: list[tuple[str, str | None]] = []
    for names in class_to_names.values():
        canonical = max(names, key=len)
        for name in names:
            results.append((name, canonical if name != canonical else None))
    return results


def _enumerate_all_nodes() -> list[dict]:
    """Walk all providers/services/nodes and return structured entries with alias detection."""
    import diagrams

    results = []
    for prov in pkgutil.iter_modules(diagrams.__path__):
        if not prov.ispkg or prov.name.startswith("_"):
            continue
        prov_fqn = f"diagrams.{prov.name}"
        try:
            prov_mod = importlib.import_module(prov_fqn)
        except ModuleNotFoundError as exc:
            if exc.name == prov_fqn:
                continue
            raise
        for svc in pkgutil.iter_modules(prov_mod.__path__):
            if svc.name.startswith("_"):
                continue
            svc_fqn = f"diagrams.{prov.name}.{svc.name}"
            try:
                svc_mod = importlib.import_module(svc_fqn)
            except ModuleNotFoundError as exc:
                if exc.name == svc_fqn:
                    continue
                raise

            for name, alias_of in _group_node_names(svc_mod):
                entry = {
                    "node": name,
                    "provider": prov.name,
                    "service": svc.name,
                    "import": _build_import_path(prov.name, svc.name, name),
                }
                if alias_of:
                    entry["alias_of"] = alias_of
                results.append(entry)

    return results


_node_index: list[dict] | None = None


def _get_node_index() -> list[dict]:
    """Lazy-initialize and return the cached node index."""
    global _node_index
    if _node_index is None:
        _node_index = _enumerate_all_nodes()
    return _node_index


@discovery.tool
def list_providers() -> list[str]:
    """List all available diagram providers (aws, gcp, azure, k8s, onprem, etc.)."""
    import diagrams

    return sorted(
        m.name
        for m in pkgutil.iter_modules(diagrams.__path__)
        if m.ispkg and not m.name.startswith("_")
    )


@discovery.tool
def list_services(provider: str) -> list[str]:
    """List service categories for a provider (e.g. 'aws' -> ['compute', 'database', ...]).

    Args:
        provider: Provider name from list_providers (e.g. 'aws', 'gcp', 'k8s').
    """
    try:
        mod = importlib.import_module(f"diagrams.{provider}")
    except ModuleNotFoundError:
        raise ToolError(
            f"Unknown provider: {provider!r}. Use list_providers to see available ones."
        )
    return sorted(m.name for m in pkgutil.iter_modules(mod.__path__) if not m.name.startswith("_"))


@discovery.tool
def list_nodes(provider: str, service: str) -> list[dict]:
    """List available node classes for a provider.service combo.

    Args:
        provider: Provider name (e.g. 'aws', 'gcp', 'k8s').
        service: Service category (e.g. 'compute', 'database', 'network').

    Returns:
        List of nodes with keys: name, import, alias_of (optional).
    """
    try:
        mod = importlib.import_module(f"diagrams.{provider}.{service}")
    except ModuleNotFoundError:
        raise ToolError(
            f"Unknown service: {provider}.{service!r}. "
            f"Use list_services('{provider}') to see available ones."
        )

    results = []
    for name, alias_of in _group_node_names(mod):
        entry = {
            "name": name,
            "import": _build_import_path(provider, service, name),
        }
        if alias_of:
            entry["alias_of"] = alias_of
        results.append(entry)

    return sorted(results, key=lambda r: r["name"])


@discovery.tool
def search_nodes(query: str) -> list[dict]:
    """Search for diagram nodes by keyword across all providers and services.

    Args:
        query: Search term (case-insensitive substring match).

    Returns:
        List of matching nodes with keys: node, provider, service, import, alias_of (optional).
        Sorted by relevance: exact match first, then prefix, then substring.
    """
    if not query or not query.strip():
        raise ToolError("Query must be a non-empty string.")

    q = query.strip().lower()
    index = _get_node_index()
    matches = [entry.copy() for entry in index if q in entry["node"].lower()]

    if not matches:
        return []

    def _sort_key(entry: dict) -> tuple[int, str]:
        name_lower = entry["node"].lower()
        if name_lower == q:
            return (0, name_lower)
        if name_lower.startswith(q):
            return (1, name_lower)
        return (2, name_lower)

    matches.sort(key=_sort_key)
    return matches
