from fastmcp import FastMCP

prompts_app = FastMCP("Prompts")


@prompts_app.prompt(description="Guide the user through building a cloud architecture diagram")
def architecture_diagram(provider: str = "") -> str:
    """Guide the user through building a cloud architecture diagram: pick a provider,
    discover nodes, compose code, and render."""
    if provider:
        return (
            f"I'd like to create a cloud architecture diagram using **{provider}** "
            f"infrastructure components.\n\n"
            f"Here's the workflow to follow:\n\n"
            f"1. Use `search_nodes` to find the {provider} components I need "
            f"(e.g., `search_nodes('load balancer')` or `search_nodes('database')`). "
            f"You can also browse with `list_services('{provider}')` then "
            f"`list_nodes('{provider}', '<service>')`.\n"
            f"2. Read `diagrams://reference/diagram` for `Diagram` constructor options "
            f"(direction, curvestyle, graph_attr).\n"
            f"3. Read `diagrams://reference/edge` for edge styling and operators "
            f"(`>>`, `<<`, `-`).\n"
            f"4. Read `diagrams://reference/cluster` for grouping nodes into clusters "
            f"(VPCs, subnets, etc.).\n"
            f"5. Compose a complete Python script using `from diagrams import ...` and "
            f"`with Diagram(...):`.\n"
            f"6. Call `render_diagram` with the code to produce the image.\n\n"
            f"Start by asking me what components and architecture I want to visualize."
        )
    return (
        "I'd like to create a cloud architecture diagram.\n\n"
        "Here's the workflow to follow:\n\n"
        "1. Ask which cloud provider to use (AWS, GCP, Azure, Kubernetes, on-prem, "
        "or multi-cloud). Use `list_providers` to show all available options.\n"
        "2. Use `search_nodes` to find the components I need "
        "(e.g., `search_nodes('load balancer')`). "
        "You can also browse with `list_services('<provider>')` then "
        "`list_nodes('<provider>', '<service>')`.\n"
        "3. Read `diagrams://reference/diagram` for `Diagram` constructor options "
        "(direction, curvestyle, graph_attr).\n"
        "4. Read `diagrams://reference/edge` for edge styling and operators "
        "(`>>`, `<<`, `-`).\n"
        "5. Read `diagrams://reference/cluster` for grouping nodes into clusters "
        "(VPCs, subnets, etc.).\n"
        "6. Compose a complete Python script using `from diagrams import ...` and "
        "`with Diagram(...):`.\n"
        "7. Call `render_diagram` with the code to produce the image.\n\n"
        "Start by asking me which cloud provider I want to use."
    )


@prompts_app.prompt(description="Guide creation of a sequence or flow diagram")
def sequence_flow(engine: str = "") -> str:
    """Guide creation of a sequence or flow diagram using Mermaid or PlantUML."""
    if engine:
        eng = engine.lower()
        if eng == "mermaid":
            return (
                "I'd like to create a sequence or flow diagram using **Mermaid**.\n\n"
                "Here's the workflow to follow:\n\n"
                "1. Read `diagrams://reference/mermaid` for the full Mermaid syntax "
                "reference (flowchart, sequence, class, ER, state, Gantt).\n"
                "2. Ask me about the participants, interactions, and flow I want to "
                "visualize.\n"
                "3. Compose a Mermaid definition string.\n"
                "4. Call `render_mermaid` with the definition to produce the image.\n\n"
                "Start by asking me what flow or sequence I want to diagram."
            )
        elif eng == "plantuml":
            return (
                "I'd like to create a sequence or flow diagram using **PlantUML**.\n\n"
                "Here's the workflow to follow:\n\n"
                "1. Read `diagrams://reference/plantuml` for the full PlantUML syntax "
                "reference (sequence, class, component, activity, state, deployment).\n"
                "2. Ask me about the participants, interactions, and flow I want to "
                "visualize.\n"
                "3. Compose a PlantUML definition wrapped in `@startuml`/`@enduml`.\n"
                "4. Call `render_plantuml` with the definition to produce the image.\n\n"
                "Start by asking me what flow or sequence I want to diagram."
            )
        return (
            f"I'd like to create a sequence or flow diagram using **{engine}**.\n\n"
            "Note: supported engines are **Mermaid** and **PlantUML**. "
            "Please ask me which one I'd prefer, or suggest one based on my needs.\n\n"
            "- **Mermaid**: Great for flowcharts, sequence diagrams, ER diagrams, "
            "Gantt charts. Read `diagrams://reference/mermaid` for syntax.\n"
            "- **PlantUML**: Great for UML-heavy diagrams (class, component, "
            "deployment, activity). Read `diagrams://reference/plantuml` for syntax.\n\n"
            "After choosing, compose the definition and call `render_mermaid` or "
            "`render_plantuml` to produce the image."
        )
    return (
        "I'd like to create a sequence or flow diagram.\n\n"
        "Here's the workflow to follow:\n\n"
        "1. Ask me what kind of diagram I need and help me choose the best engine:\n"
        "   - **Mermaid** (`render_mermaid`): Flowcharts, sequence diagrams, ER diagrams, "
        "state diagrams, Gantt charts. Read `diagrams://reference/mermaid` for syntax.\n"
        "   - **PlantUML** (`render_plantuml`): Sequence, class, component, activity, "
        "state, deployment diagrams. Read `diagrams://reference/plantuml` for syntax.\n"
        "2. Ask me about the participants, interactions, and flow I want to visualize.\n"
        "3. Compose the diagram definition in the chosen syntax.\n"
        "4. Call `render_mermaid` or `render_plantuml` to produce the image.\n\n"
        "Start by asking me what I want to diagram so we can pick the right engine."
    )


@prompts_app.prompt(description="Walk through multi-cloud service comparison")
def compare_providers(service_role: str = "") -> str:
    """Walk through comparing equivalent services across AWS, GCP, and Azure."""
    if service_role:
        return (
            f"I'd like to compare equivalent cloud services across providers for "
            f"the **{service_role}** infrastructure role.\n\n"
            f"Here's the workflow to follow:\n\n"
            f"1. Call `find_equivalent` with a node from the '{service_role}' category "
            f"to see equivalent services across AWS, GCP, and Azure.\n"
            f"2. Present the comparison: show each provider's equivalent service with "
            f"its import path.\n"
            f"3. Optionally, use `render_diagram` to produce a side-by-side "
            f"architecture diagram showing the equivalent services from each provider.\n\n"
            f"Start by calling `find_equivalent` for this role."
        )
    return (
        "I'd like to compare equivalent services across cloud providers "
        "(AWS, GCP, Azure).\n\n"
        "Here's the workflow to follow:\n\n"
        "1. Call `list_categories` to show all available infrastructure role "
        "categories (e.g., virtual_machine, serverless_function, load_balancer, "
        "relational_database).\n"
        "2. Ask me which role or category I'm interested in.\n"
        "3. Call `find_equivalent` with a node from that category to see the "
        "equivalent services across AWS, GCP, and Azure.\n"
        "4. Present the comparison: show each provider's equivalent service with "
        "its import path.\n"
        "5. Optionally, use `render_diagram` to produce a side-by-side "
        "architecture diagram showing the equivalent services from each provider.\n\n"
        "Start by showing me the available categories with `list_categories`."
    )


@prompts_app.prompt(
    description=(
        "Minimal-friction path: describe what to visualize and the best engine is"
        " picked automatically"
    )
)
def quick_sketch(description: str = "") -> str:
    """Minimal-friction diagram creation: describe what to visualize, and the best
    rendering engine is selected automatically."""
    if description:
        return (
            f"I want to create a diagram of: **{description}**\n\n"
            "Pick the best rendering engine based on what I described:\n\n"
            "- **Cloud architecture** (AWS, GCP, Azure, K8s, on-prem infrastructure) → "
            "use `search_nodes` to find components, read `diagrams://reference/diagram`, "
            "then `render_diagram`\n"
            "- **Flowcharts, sequences, ER diagrams, Gantt charts** → "
            "read `diagrams://reference/mermaid`, then `render_mermaid`\n"
            "- **UML-heavy diagrams** (class, component, deployment, activity) → "
            "read `diagrams://reference/plantuml`, then `render_plantuml`\n\n"
            "Go ahead and create the diagram — ask clarifying questions only if "
            "the description is ambiguous."
        )
    return (
        "I want to create a diagram but I'm not sure which tool to use.\n\n"
        "Ask me what I want to visualize, then pick the best rendering engine:\n\n"
        "- **Cloud architecture** (AWS, GCP, Azure, K8s, on-prem infrastructure) → "
        "use `search_nodes` to find components, read `diagrams://reference/diagram`, "
        "then `render_diagram`\n"
        "- **Flowcharts, sequences, ER diagrams, Gantt charts** → "
        "read `diagrams://reference/mermaid`, then `render_mermaid`\n"
        "- **UML-heavy diagrams** (class, component, deployment, activity) → "
        "read `diagrams://reference/plantuml`, then `render_plantuml`\n\n"
        "Start by asking me what I'd like to diagram."
    )
