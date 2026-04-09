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


@references.resource(
    "diagrams://reference/mermaid",
    mime_type="text/markdown",
)
def mermaid_reference() -> str:
    """Mermaid diagram syntax reference — common diagram types and examples."""
    return """\
# Mermaid Syntax Reference

Render Mermaid diagrams with `render_mermaid(definition)`.

## Flowchart

```mermaid
graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[OK]
    B -->|No| D[Cancel]
```

## Sequence Diagram

```mermaid
sequenceDiagram
    participant A as Alice
    participant B as Bob
    A->>B: Hello Bob
    B-->>A: Hi Alice
    A->>B: How are you?
    B-->>A: Great!
```

## Class Diagram

```mermaid
classDiagram
    Animal <|-- Duck
    Animal <|-- Fish
    Animal : +int age
    Animal : +String gender
    Animal : +isMammal()
    Duck : +String beakColor
    Duck : +swim()
    Duck : +quack()
```

## ER Diagram

```mermaid
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE-ITEM : contains
    PRODUCT ||--o{ LINE-ITEM : "ordered in"
```

## State Diagram

```mermaid
stateDiagram-v2
    [*] --> Still
    Still --> [*]
    Still --> Moving
    Moving --> Still
    Moving --> Crash
    Crash --> [*]
```

## Gantt Chart

```mermaid
gantt
    title Project Schedule
    dateFormat YYYY-MM-DD
    section Phase 1
    Task A :a1, 2024-01-01, 30d
    Task B :after a1, 20d
```

## Key Syntax Notes

- **Node shapes**: `[rect]`, `(round)`, `{diamond}`, `([stadium])`, `[[subroutine]]`,
  `[(cylinder)]`, `((circle))`
- **Arrow types**: `-->` solid, `-.->` dotted, `==>` thick, `--text-->` labeled
- **Subgraphs**: `subgraph title ... end` for grouping
- **Direction**: `graph TD` (top-down), `graph LR` (left-right), `graph BT`, `graph RL`
"""


@references.resource(
    "diagrams://reference/plantuml",
    mime_type="text/markdown",
)
def plantuml_reference() -> str:
    """PlantUML diagram syntax reference — common diagram types and examples."""
    return """\
# PlantUML Syntax Reference

Render PlantUML diagrams with `render_plantuml(definition)`.
All definitions must be wrapped in `@startuml` / `@enduml`.

## Sequence Diagram

```plantuml
@startuml
Alice -> Bob: Authentication Request
Bob --> Alice: Authentication Response
Alice -> Bob: Another request
Bob --> Alice: Another response
@enduml
```

## Class Diagram

```plantuml
@startuml
class User {
  +String name
  +String email
  +login()
}
class Order {
  +int id
  +Date date
  +ship()
}
User "1" -- "*" Order : places
@enduml
```

## Component Diagram

```plantuml
@startuml
package "Frontend" {
  [Web App]
  [Mobile App]
}
package "Backend" {
  [API Server]
  [Auth Service]
}
database "Database" {
  [PostgreSQL]
}
[Web App] --> [API Server]
[Mobile App] --> [API Server]
[API Server] --> [Auth Service]
[API Server] --> [PostgreSQL]
@enduml
```

## Activity Diagram

```plantuml
@startuml
start
:Receive request;
if (Valid?) then (yes)
  :Process request;
  :Send response;
else (no)
  :Return error;
endif
stop
@enduml
```

## State Diagram

```plantuml
@startuml
[*] --> Idle
Idle --> Processing : submit
Processing --> Done : complete
Processing --> Error : fail
Error --> Idle : retry
Done --> [*]
@enduml
```

## Deployment Diagram

```plantuml
@startuml
node "Web Server" {
  [Nginx]
  [App]
}
node "DB Server" {
  [PostgreSQL]
}
[Nginx] --> [App]
[App] --> [PostgreSQL]
@enduml
```

## Key Syntax Notes

- **Arrows**: `->` solid, `-->` dashed, `..>` dotted, `->>` async, `->o` with circle
- **Stereotypes**: `<<interface>>`, `<<abstract>>`, `<<enum>>`
- **Notes**: `note left of X : text`, `note right of X : text`, `note over X : text`
- **Colors**: `#Red`, `#FF0000`, `skinparam backgroundColor #EEEEEE`
- **Grouping**: `package`, `node`, `folder`, `frame`, `cloud`, `database`
"""
