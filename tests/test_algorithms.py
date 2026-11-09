import copy
import math
import random
import networkx as nx
import pytest
from algotutor.algorithms import execute, InputError
from algotutor.catalog import CATALOG, example, TOOL_SCHEMAS
from jsonschema import validate


def graph(vertices, edges, directed=False):
    return {"vertices": vertices, "directed": directed, "edges": [{"from": u, "to": v, "weight": w} for u, v, w in edges]}


@pytest.mark.parametrize("name", [r[0] for r in CATALOG])
def test_examples_have_valid_schemas_and_execute(name):
    args = example(name)
    validate(args, next(s["input_schema"] for s in TOOL_SCHEMAS if s["name"] == name))
    original = copy.deepcopy(args)
    result = execute(name, args)
    assert result["algorithm"] == name
    assert args == original  # user input must not be mutated


@pytest.mark.parametrize("seed", range(12))
def test_shortest_paths_against_networkx(seed):
    rng = random.Random(seed)
    vertices = list("ABCDEFG")
    edges = [(u, v, rng.randint(0, 20)) for u in vertices for v in vertices if u != v and rng.random() < .25]
    data = graph(vertices, edges, True)
    reference = nx.DiGraph()
    reference.add_nodes_from(vertices)
    reference.add_weighted_edges_from(edges)
    fw = execute("floyd_warshall", {"graph": data})
    for source in vertices:
        expected = nx.single_source_dijkstra_path_length(reference, source)
        for name in ("dijkstra", "bellman_ford"):
            result = execute(name, {"graph": data, "source": source})
            assert result["distances"] == {v: expected.get(v) for v in vertices}
            assert fw["distances"][source] == result["distances"]
            for v, path in result["paths"].items():
                if path:
                    assert path[0] == source and path[-1] == v
                    assert sum(reference[u][w]["weight"] for u, w in zip(path, path[1:])) == expected[v]
        bfs = execute("bfs", {"graph": data, "source": source})
        shortest = nx.single_source_shortest_path_length(reference, source)
        assert bfs["distances"] == {v: shortest.get(v) for v in vertices}


def test_negative_cycle_affects_only_reachable_downstream_nodes():
    data = graph(list("SABCDEZ"), [("S", "A", 1), ("A", "B", -3), ("B", "A", 1), ("B", "C", 2), ("S", "D", 8), ("Z", "Z", -1)], True)
    bf = execute("bellman_ford", {"graph": data, "source": "S"})
    assert set(bf["affected_vertices"]) == set("ABC")
    assert bf["distances"] == {"S": 0, "A": "-infinity", "B": "-infinity", "C": "-infinity", "D": 8, "E": None, "Z": None}
    fw = execute("floyd_warshall", {"graph": data})
    assert fw["distances"]["S"] == bf["distances"]
    assert fw["distances"]["Z"]["Z"] == "-infinity"
    assert fw["paths"]["S"]["D"] == ["S", "D"]


@pytest.mark.parametrize("seed", range(8))
def test_negative_dag_paths(seed):
    rng = random.Random(seed)
    vertices = list("ABCDEFGH")
    edges = [(u, v, rng.randint(-8, 10)) for i, u in enumerate(vertices) for v in vertices[i + 1:] if rng.random() < .4]
    data = graph(vertices, edges, True)
    reference = nx.DiGraph()
    reference.add_nodes_from(vertices)
    reference.add_weighted_edges_from(edges)
    fw = execute("floyd_warshall", {"graph": data})
    for source in vertices:
        lengths = nx.single_source_bellman_ford_path_length(reference, source)
        expected = {v: lengths.get(v) for v in vertices}
        assert execute("bellman_ford", {"graph": data, "source": source})["distances"] == expected
        assert fw["distances"][source] == expected
        for v, path in fw["paths"][source].items():
            if path:
                assert sum(reference[u][w]["weight"] for u, w in zip(path, path[1:])) == lengths[v]


@pytest.mark.parametrize("seed", range(12))
def test_mst_and_biconnectivity_against_networkx(seed):
    rng = random.Random(seed)
    vertices = list("ABCDEFGH")
    edges = [(u, v, rng.randint(-5, 12)) for i, u in enumerate(vertices) for j, v in enumerate(vertices) if i < j and (j == i + 1 or rng.random() < .2)]
    data = graph(vertices, edges)
    reference = nx.Graph()
    reference.add_weighted_edges_from(edges)
    expected_weight = nx.minimum_spanning_tree(reference).size(weight="weight")
    for name in ("prim", "kruskal"):
        output = execute(name, {"graph": data})
        assert output["total_weight"] == expected_weight
        tree = nx.Graph((e["from"], e["to"]) for e in output["tree_edges"])
        assert nx.is_tree(tree)
    result = execute("biconnected", {"graph": data})
    assert set(result["articulation_points"]) == set(nx.articulation_points(reference))
    actual = {frozenset(frozenset((e["from"], e["to"])) for e in component) for component in result["components"]}
    expected = {frozenset(frozenset(e) for e in component) for component in nx.biconnected_component_edges(reference)}
    assert actual == expected


@pytest.mark.parametrize("seed", range(15))
def test_max_flow_conservation_cut_and_antiparallel_edges(seed):
    rng = random.Random(seed)
    vertices = list("SABCDT")
    edges = [(u, v, rng.randint(0, 20)) for u in vertices for v in vertices if u != v and rng.random() < .4]
    reference = nx.DiGraph()
    reference.add_nodes_from(vertices)
    for u, v, w in edges:
        reference.add_edge(u, v, capacity=w)
    expected = nx.maximum_flow_value(reference, "S", "T")
    for name in ("ford_fulkerson", "edmonds_karp"):
        output = execute(name, {"graph": graph(vertices, edges, True), "source": "S", "sink": "T"})
        assert output["max_flow"] == expected == output["min_cut"]["capacity"]
        balance = dict.fromkeys(vertices, 0)
        for e in output["edge_flows"]:
            assert 0 <= e["flow"] <= e["capacity"]
            balance[e["from"]] -= e["flow"]
            balance[e["to"]] += e["flow"]
        assert balance == {v: -expected if v == "S" else expected if v == "T" else 0 for v in vertices}
        if name == "edmonds_karp":
            lengths = [len(s["path"]) for s in output["steps"]]
            assert lengths == sorted(lengths)


def test_dfs_forest_and_parent_intervals():
    data = graph(list("ABCDEF"), [("A", "B", 1), ("B", "C", 1), ("C", "A", 1), ("D", "E", 1)])
    output = execute("dfs", {"graph": data, "source": "D"})
    assert output["order"][0] == "D"
    assert set(output["discovery"].values()) | set(output["finish"].values()) == set(range(1, 13))
    for v, p in output["parents"].items():
        assert output["discovery"][v] < output["finish"][v]
        if p:
            assert output["discovery"][p] < output["discovery"][v] < output["finish"][v] < output["finish"][p]


def test_union_find_transitivity_and_repeated_union():
    output = execute("union_find", {"elements": list("ABCD"), "operations": [
        {"op": "union", "a": "A", "b": "B"}, {"op": "union", "a": "B", "b": "C"},
        {"op": "union", "a": "A", "b": "C"}, {"op": "find", "a": "C"}]})
    assert output["groups"] == [["A", "B", "C"], ["D"]]
    assert output["steps"][2]["result"] is False
    assert output["steps"][3]["result"] == "A"


@pytest.mark.parametrize("name,args", [
    ("dijkstra", {"graph": graph(["A", "B"], [("A", "B", -1)]), "source": "A"}),
    ("bfs", {"graph": graph(["A"], []), "source": "B"}),
    ("prim", {"graph": graph(["A", "B"], [])}),
    ("kruskal", {"graph": graph(["A", "B"], [("A", "B", 1)], True)}),
    ("bfs", {"graph": graph(["A", "B"], [("A", "B", math.nan)]), "source": "A"}),
    ("graph_scan", {"graph": graph(["A", "A"], [])}),
    ("graph_scan", {"graph": graph(["A", "B"], [("A", "B", 1), ("B", "A", 1)])}),
    ("graph_scan", {"graph": graph(["A"], [("A", "B", 1)])}),
    ("graph_scan", {"graph": {"vertices": ["A"], "edges": [], "directed": "false"}}),
    ("ford_fulkerson", {"graph": graph(["S", "T"], [("S", "T", 1.5)], True), "source": "S", "sink": "T"}),
    ("edmonds_karp", {"graph": graph(["S"], [], True), "source": "S", "sink": "S"}),
    ("bfs", {}), ("not_a_tool", {}), ("union_find", {"elements": ["A"], "operations": [{"op": "delete", "a": "A"}]})
])
def test_invalid_inputs(name, args):
    with pytest.raises(InputError):
        execute(name, args)


def test_single_vertex_and_disconnected_components():
    for name in ("prim", "kruskal"):
        assert execute(name, {"graph": graph(["A"], [])})["total_weight"] == 0
    result = execute("biconnected", {"graph": graph(list("ABCD"), [("A", "B", 1), ("A", "C", 1)])})
    assert result["articulation_points"] == ["A"]
    assert result["isolated_vertices"] == ["D"]
