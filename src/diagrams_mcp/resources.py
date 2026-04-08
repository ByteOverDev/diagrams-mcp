from fastmcp import FastMCP

references = FastMCP("References")


@references.resource(
    "diagrams://reference/diagram",
    mime_type="text/markdown",
)
def diagram_reference() -> str:
    """Diagram constructor reference — parameters, defaults, and usage."""
    return """\
# Diagram Constructor Reference

```python
from diagrams import Diagram

with Diagram(name, **options):
    ...
```

## Parameters

| Parameter    | Type                | Default   | Description |
|--------------|---------------------|-----------|-------------|
| name       | str              | ""      | Diagram title; derives filename |
| filename   | str              | ""      | Output filename (no extension) |
| direction  | str              | "LR"    | "LR", "RL", "TB", or "BT" |
| curvestyle | str              | "ortho" | "ortho" or "curved" |
| outformat  | str or list[str] | "png"   | "png", "jpg", "svg", "pdf", "dot" |
| autolabel  | bool             | False   | Prepend class name to labels |
| show       | bool             | True    | Open image after render (False in MCP) |
| strict     | bool             | False   | Merge duplicate edges |
| graph_attr | dict or None     | None    | Extra Graphviz graph attributes |
| node_attr  | dict or None     | None    | Extra Graphviz node attributes |
| edge_attr  | dict or None     | None    | Extra Graphviz edge attributes |

## Default Graph Attributes

pad="2.0", splines="ortho", nodesep="0.60", ranksep="0.75",
fontname="Sans-Serif", fontsize="15", fontcolor="#2D3436"

## Example

```python
with Diagram("Web Service", direction="TB", curvestyle="curved",
             graph_attr={"bgcolor": "transparent"}):
    ...
```
"""


@references.resource(
    "diagrams://reference/edge",
    mime_type="text/markdown",
)
def edge_reference() -> str:
    """Edge constructor reference — parameters, operators, and styling."""
    return """\
# Edge Reference

```python
from diagrams import Edge
```

## Parameters

| Parameter | Type   | Default | Description |
|-----------|--------|---------|-------------|
| label     | str    | ""      | Edge label text |
| color     | str    | ""      | Graphviz color name or hex (e.g. "red", "#FF0000") |
| style     | str    | ""      | Line style: "solid", "dashed", "dotted", "bold", "invis" |
| **attrs   | dict   | —       | Any additional Graphviz edge attributes |

Extra attributes commonly used via **attrs:
- minlen: str number for minimum edge length
- headport / tailport: "n", "s", "e", "w", "ne", "nw", "se", "sw"

## Operators

| Operator | Direction     | Example |
|----------|---------------|---------|
| >>       | left to right | `node_a >> node_b` |
| <<       | right to left | `node_a << node_b` |
| -        | no direction  | `node_a - node_b` |

## Chaining

```python
node_a >> node_b >> node_c          # chain connections
node_a >> Edge(label="HTTPS") >> node_b  # labeled edge
[node_a, node_b] >> node_c          # fan-in
node_a >> [node_b, node_c]          # fan-out
```

## Example

```python
web >> Edge(label="HTTPS", color="darkgreen", style="bold") >> api
api >> Edge(style="dashed") >> cache
```
"""


@references.resource(
    "diagrams://reference/cluster",
    mime_type="text/markdown",
)
def cluster_reference() -> str:
    """Cluster constructor reference — parameters, nesting, and styling."""
    return """\
# Cluster Reference

```python
from diagrams import Cluster
```

## Parameters

| Parameter  | Type         | Default    | Description |
|------------|--------------|------------|-------------|
| label      | str          | "cluster"  | Cluster label text |
| direction  | str          | "LR"       | Internal layout direction: "LR", "RL", "TB", "BT" |
| graph_attr | dict or None | None       | Extra Graphviz subgraph attributes |

## Default Attributes

shape="box", style="rounded", labeljust="l", pencolor="#AEB6BE",
fontname="Sans-Serif", fontsize="12"

Background color cycles automatically by nesting depth:
depth 0: #E5F5FD, depth 1: #EBF3E7, depth 2: #ECE8F6, depth 3: #FDF7E3

## Nesting

```python
with Diagram("Nested"):
    with Cluster("VPC"):
        with Cluster("Public Subnet"):
            web = EC2("web")
        with Cluster("Private Subnet"):
            db = RDS("db")
    web >> db
```

## Styling

```python
with Cluster("Styled", graph_attr={
    "bgcolor": "#FAFAFA",
    "style": "dashed",
    "color": "red",
    "penwidth": "2.0",
}):
    ...
```

## Aliases

`Group` is an alias for `Cluster`:

```python
from diagrams import Cluster, Group  # Group == Cluster
```
"""
