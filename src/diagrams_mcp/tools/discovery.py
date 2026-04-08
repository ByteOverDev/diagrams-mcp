import importlib
import pkgutil

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

discovery = FastMCP("Discovery")


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
def list_nodes(provider: str, service: str) -> list[str]:
    """List available node classes for a provider.service combo.

    Args:
        provider: Provider name (e.g. 'aws', 'gcp', 'k8s').
        service: Service category (e.g. 'compute', 'database', 'network').
    """
    try:
        mod = importlib.import_module(f"diagrams.{provider}.{service}")
    except ModuleNotFoundError:
        raise ToolError(
            f"Unknown service: {provider}.{service!r}. "
            f"Use list_services('{provider}') to see available ones."
        )
    return sorted(
        name
        for name in dir(mod)
        if not name.startswith("_") and isinstance(getattr(mod, name), type)
    )
