"""Anthropic-native tool schemas and editable classroom examples."""
from copy import deepcopy

CATALOG = [
    ("graph_scan", "ייצוג וסריקת גרף", 1, "Adjacency lists, vertices and edges."),
    ("bfs", "BFS · חיפוש לרוחב", 2, "Unweighted shortest paths by BFS; edge weights are ignored."),
    ("dijkstra", "דייקסטרה", 3, "Single-source shortest paths. Rejects any negative edge."),
    ("bellman_ford", "בלמן–פורד", 4, "Shortest paths with negative edges and reachable negative-cycle detection."),
    ("floyd_warshall", "פלויד–וורשל", 5, "All-pairs shortest paths, paths and negative-cycle detection."),
    ("prim", "פרים", 6, "Minimum spanning tree of a connected undirected weighted graph."),
    ("kruskal", "קרוסקל", 7, "Minimum spanning tree using sorted edges and Union-Find."),
    ("union_find", "Union–Find", 7, "Union by rank and path compression; show groups after each operation."),
    ("dfs", "DFS · חיפוש לעומק", 8, "DFS forest with discovery/finish times and tree edges."),
    ("biconnected", "צמתי הפרדה ורכיבים דו־קשירים", 9, "Articulation points and vertex-biconnected components represented by their edges, using DFS low values."),
    ("ford_fulkerson", "פורד–פולקרסון", 10, "Maximum flow with a stack-based augmenting-path search and min cut; integer capacities 0..50."),
    ("edmonds_karp", "אדמונדס–קארפ", 11, "Maximum flow using BFS augmenting paths and min cut; integer capacities 0..50."),
]

GRAPH_SCHEMA = {"type": "object", "properties": {
    "vertices": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 16},
    "directed": {"type": "boolean"},
    "edges": {"type": "array", "maxItems": 60, "items": {"type": "object", "properties": {
        "from": {"type": "string"}, "to": {"type": "string"}, "weight": {"type": "number"}},
        "required": ["from", "to", "weight"], "additionalProperties": False}}},
    "required": ["vertices", "edges", "directed"], "additionalProperties": False}


def schema(name, description):
    properties, required = {"graph": deepcopy(GRAPH_SCHEMA)}, ["graph"]
    if name in ("bfs", "dijkstra", "bellman_ford", "prim", "dfs", "ford_fulkerson", "edmonds_karp"):
        properties["source"] = {"type": "string", "description": "Start vertex, exactly as in graph.vertices."}
        if name not in ("prim", "dfs"):
            required.append("source")
    if name in ("ford_fulkerson", "edmonds_karp"):
        properties["sink"] = {"type": "string", "description": "Sink vertex, distinct from source."}
        required.append("sink")
    if name == "union_find":
        properties = {"elements": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 30},
                      "operations": {"type": "array", "maxItems": 100, "items": {"type": "object", "properties": {
                          "op": {"type": "string", "enum": ["find", "union"]}, "a": {"type": "string"}, "b": {"type": "string"}},
                          "required": ["op", "a"], "additionalProperties": False}}}
        required = ["elements", "operations"]
    return {"name": name, "description": description + " Returns a deterministic result and a step trace. Never invent missing graph input.",
            "input_schema": {"type": "object", "properties": properties, "required": required, "additionalProperties": False}}


TOOL_SCHEMAS = [schema(name, description) for name, _, _, description in CATALOG]


def example(name):
    if name == "union_find":
        return {"elements": ["A", "B", "C", "D"], "operations": [
            {"op": "union", "a": "A", "b": "B"}, {"op": "union", "a": "C", "b": "D"},
            {"op": "union", "a": "B", "b": "D"}, {"op": "find", "a": "C"}]}
    flow = name in ("ford_fulkerson", "edmonds_karp")
    vertices = ["S", "A", "B", "T"] if flow else ["A", "B", "C", "D", "E"]
    raw = [("S", "A", 8), ("S", "B", 5), ("A", "B", 3), ("A", "T", 5), ("B", "T", 8)] if flow else [
        ("A", "B", 4), ("A", "C", 2), ("B", "C", 1), ("B", "D", 5), ("C", "D", 8), ("D", "E", 2)]
    directed = flow or name in ("dijkstra", "bellman_ford", "floyd_warshall")
    if name == "bellman_ford":
        raw[2] = ("B", "C", -1)
    args = {"graph": {"vertices": vertices, "directed": directed,
                      "edges": [{"from": u, "to": v, "weight": w} for u, v, w in raw]}}
    if name in ("bfs", "dijkstra", "bellman_ford", "prim", "dfs") or flow:
        args["source"] = vertices[0]
    if flow:
        args["sink"] = "T"
    return args


def public_catalog():
    return [{"name": name, "label": label, "lecture": lecture, "description": desc, "example": example(name)}
            for name, label, lecture, desc in CATALOG]
