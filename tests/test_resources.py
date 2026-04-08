from diagrams_mcp.resources import cluster_reference, diagram_reference, edge_reference


def test_diagram_reference_contains_parameters():
    text = diagram_reference()
    assert "direction" in text
    assert "outformat" in text
    assert "graph_attr" in text
    assert "curvestyle" in text


def test_edge_reference_contains_operators():
    text = edge_reference()
    assert ">>" in text
    assert "<<" in text
    assert "label" in text
    assert "style" in text


def test_cluster_reference_contains_nesting():
    text = cluster_reference()
    assert "Cluster" in text
    assert "graph_attr" in text
    assert "Group" in text
