"""Deterministic teaching implementations. No LLM, network, or database required.

Tie breaks follow input vertex/edge order. None means unreachable; '-infinity'
means that a reachable negative cycle makes a shortest distance unbounded.
"""
from collections import deque
import heapq
import math


class InputError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InputError(message)


class Graph:
    def __init__(self, data):
        require(isinstance(data, dict), "יש להזין אובייקט graph.")
        self.vertices = data.get("vertices")
        require(isinstance(self.vertices, list) and 1 <= len(self.vertices) <= 16,
                "הגרף חייב להכיל בין 1 ל־16 צמתים.")
        require(all(isinstance(v, str) and 0 < len(v) <= 24 for v in self.vertices),
                "שמות הצמתים חייבים להיות מחרוזות באורך 1–24 תווים.")
        require(len(set(self.vertices)) == len(self.vertices), "שמות הצמתים חייבים להיות ייחודיים.")
        self.directed = data.get("directed", False)
        require(type(self.directed) is bool, "directed חייב להיות true או false.")
        self.index = {v: i for i, v in enumerate(self.vertices)}
        raw = data.get("edges")
        require(isinstance(raw, list) and len(raw) <= 60, "יש להזין רשימה של עד 60 קשתות.")
        self.edges, self.adj = [], {v: [] for v in self.vertices}
        seen = set()
        for i, edge in enumerate(raw):
            require(isinstance(edge, dict), "כל קשת חייבת להיות אובייקט עם from ו־to.")
            u, v, w = edge.get("from"), edge.get("to"), edge.get("weight", 1)
            require(isinstance(u, str) and isinstance(v, str) and u in self.index and v in self.index,
                    "כל קצה של קשת חייב להופיע ברשימת הצמתים.")
            require(type(w) in (int, float) and math.isfinite(w) and abs(w) <= 1_000_000,
                    "משקל חייב להיות מספר סופי שערכו המוחלט עד מיליון.")
            key = (u, v) if self.directed else tuple(sorted((u, v)))
            require(key not in seen, "בגרסה זו אין תמיכה בקשתות מקבילות; הזינו כל קשת פעם אחת.")
            seen.add(key)
            self.edges.append({"from": u, "to": v, "weight": w, "id": i})
            self.adj[u].append((v, w, i))
            if not self.directed and u != v:
                self.adj[v].append((u, w, i))

    def vertex(self, v):
        require(isinstance(v, str) and v in self.index, "צומת המקור/היעד חייב להופיע בגרף.")
        return v

    def arcs(self):
        return [(u, v, w, i) for u in self.vertices for v, w, i in self.adj[u]]

    def undirected(self):
        require(not self.directed, "האלגוריתם דורש גרף לא מכוון (directed: false).")


def clean_distances(dist):
    return {v: None if d == math.inf else "-infinity" if d == -math.inf else d for v, d in dist.items()}


def shortest_output(g, source, dist, parent):
    paths = {}
    for v in g.vertices:
        if not math.isfinite(dist[v]):
            paths[v] = None
            continue
        path, current = [], v
        while current is not None and len(path) <= len(g.vertices):
            path.append(current)
            current = parent[current]
        paths[v] = list(reversed(path)) if current is None and path[-1] == source else None
    return {"distances": clean_distances(dist), "paths": paths, "parents": parent}


def graph_scan(graph, **_):
    g = Graph(graph)
    return {"vertices": g.vertices, "edges": g.edges,
            "adjacency": {u: [{"vertex": v, "weight": w} for v, w, _ in g.adj[u]] for u in g.vertices},
            "vertex_count": len(g.vertices), "edge_count": len(g.edges),
            "steps": [{"event": "scan", "vertex": u, "neighbors": [v for v, _, _ in g.adj[u]]} for u in g.vertices]}


def bfs(graph, source, **_):
    g = Graph(graph)
    g.vertex(source)
    dist, parent = dict.fromkeys(g.vertices, math.inf), dict.fromkeys(g.vertices)
    dist[source] = 0
    queue, order, steps, tree = deque([source]), [], [], []
    while queue:
        u = queue.popleft()
        order.append(u)
        for v, _, eid in g.adj[u]:
            if dist[v] == math.inf:
                dist[v], parent[v] = dist[u] + 1, u
                tree.append(eid)
                queue.append(v)
        steps.append({"event": "visit", "vertex": u, "queue": list(queue), "distances": clean_distances(dist)})
    return {**shortest_output(g, source, dist, parent), "order": order, "tree_edge_ids": tree,
            "steps": steps, "note": "BFS מודד מספר קשתות; הוא מתעלם ממשקלים."}


def dijkstra(graph, source, **_):
    g = Graph(graph)
    g.vertex(source)
    require(all(e["weight"] >= 0 for e in g.edges), "דייקסטרה אינו תומך במשקלים שליליים. השתמשו בבלמן–פורד.")
    dist, parent = dict.fromkeys(g.vertices, math.inf), dict.fromkeys(g.vertices)
    dist[source], queue, settled, steps = 0, [(0, g.index[source], source)], set(), []
    while queue:
        _, _, u = heapq.heappop(queue)
        if u in settled:
            continue
        settled.add(u)
        relaxed = []
        for v, w, eid in g.adj[u]:
            if dist[u] + w < dist[v]:
                dist[v], parent[v] = dist[u] + w, u
                relaxed.append(eid)
                heapq.heappush(queue, (dist[v], g.index[v], v))
        steps.append({"event": "settle", "vertex": u, "relaxed_edge_ids": relaxed, "distances": clean_distances(dist)})
    return {**shortest_output(g, source, dist, parent), "steps": steps}


def bellman_ford(graph, source, **_):
    g = Graph(graph)
    g.vertex(source)
    dist, parent = dict.fromkeys(g.vertices, math.inf), dict.fromkeys(g.vertices)
    dist[source], steps = 0, []
    arcs = g.arcs()
    for iteration in range(1, len(g.vertices)):
        changed = []
        for u, v, w, eid in arcs:
            if dist[u] != math.inf and dist[u] + w < dist[v]:
                dist[v], parent[v] = dist[u] + w, u
                changed.append(eid)
        steps.append({"event": "relax_pass", "iteration": iteration,
                      "relaxed_edge_ids": changed, "distances": clean_distances(dist)})
        if not changed:
            break
    affected = {v for u, v, w, _ in arcs if dist[u] != math.inf and dist[u] + w < dist[v]}
    queue = deque(affected)
    while queue:
        for v, _, _ in g.adj[queue.popleft()]:
            if v not in affected:
                affected.add(v)
                queue.append(v)
    for v in affected:
        dist[v], parent[v] = -math.inf, None
    return {**shortest_output(g, source, dist, parent), "negative_cycle": bool(affected),
            "affected_vertices": [v for v in g.vertices if v in affected], "steps": steps}


def floyd_warshall(graph, **_):
    g = Graph(graph)
    dist = {u: {v: 0 if u == v else math.inf for v in g.vertices} for u in g.vertices}
    nxt = {u: {v: None for v in g.vertices} for u in g.vertices}
    for u, v, w, _ in g.arcs():
        if w < dist[u][v]:
            dist[u][v], nxt[u][v] = w, v
    steps = []
    for k in g.vertices:
        changes = []
        for u in g.vertices:
            for v in g.vertices:
                candidate = dist[u][k] + dist[k][v]
                if candidate < dist[u][v]:
                    dist[u][v], nxt[u][v] = candidate, nxt[u][k]
                    changes.append([u, v])
        steps.append({"event": "intermediate", "vertex": k, "changed_pairs": changes,
                      "distances": {u: clean_distances(row) for u, row in dist.items()}})
    negative = [v for v in g.vertices if dist[v][v] < 0]
    affected = {(u, v) for k in negative for u in g.vertices for v in g.vertices
                if dist[u][k] != math.inf and dist[k][v] != math.inf}
    paths = {u: {} for u in g.vertices}
    for u in g.vertices:
        for v in g.vertices:
            if (u, v) in affected:
                dist[u][v], paths[u][v] = -math.inf, None
            elif dist[u][v] == math.inf:
                paths[u][v] = None
            elif u == v:
                paths[u][v] = [u]
            else:
                path, current = [u], u
                while current != v and len(path) <= len(g.vertices):
                    current = nxt[current][v]
                    if current is None:
                        break
                    path.append(current)
                paths[u][v] = path if current == v else None
    return {"distances": {u: clean_distances(row) for u, row in dist.items()}, "paths": paths,
            "negative_cycle": bool(negative), "negative_cycle_vertices": negative, "steps": steps}


class UnionFind:
    def __init__(self, elements):
        self.parent = {v: v for v in elements}
        self.rank = dict.fromkeys(elements, 0)

    def find(self, v):
        if self.parent[v] != v:
            self.parent[v] = self.find(self.parent[v])
        return self.parent[v]

    def union(self, u, v):
        u, v = self.find(u), self.find(v)
        if u == v:
            return False
        if self.rank[u] < self.rank[v]:
            u, v = v, u
        self.parent[v] = u
        if self.rank[u] == self.rank[v]:
            self.rank[u] += 1
        return True

    def groups(self):
        groups = {}
        for v in self.parent:
            groups.setdefault(self.find(v), []).append(v)
        return list(groups.values())


def union_find(elements, operations, **_):
    require(isinstance(elements, list) and 1 <= len(elements) <= 30 and
            all(isinstance(v, str) and 0 < len(v) <= 24 for v in elements), "יש להזין 1–30 שמות איברים.")
    require(len(set(elements)) == len(elements), "האיברים חייבים להיות ייחודיים.")
    require(isinstance(operations, list) and len(operations) <= 100, "מותרות עד 100 פעולות.")
    uf, steps = UnionFind(elements), []
    for op in operations:
        require(isinstance(op, dict) and op.get("op") in ("find", "union"), "פעולה חייבת להיות find או union.")
        u = op.get("a")
        require(isinstance(u, str) and u in uf.parent, "איבר a אינו קיים.")
        if op["op"] == "union":
            v = op.get("b")
            require(isinstance(v, str) and v in uf.parent, "איבר b אינו קיים.")
            result = uf.union(u, v)
        else:
            result = uf.find(u)
        steps.append({"event": op["op"], "operation": op, "result": result, "groups": uf.groups()})
    return {"groups": uf.groups(), "parents": dict(uf.parent), "steps": steps}


def kruskal(graph, **_):
    g = Graph(graph)
    g.undirected()
    uf, chosen, steps = UnionFind(g.vertices), [], []
    for edge in sorted(g.edges, key=lambda e: (e["weight"], e["id"])):
        accepted = uf.union(edge["from"], edge["to"])
        if accepted:
            chosen.append(edge)
        steps.append({"event": "accept" if accepted else "reject_cycle", "edge": edge,
                      "selected_edge_ids": [e["id"] for e in chosen], "groups": uf.groups()})
    require(len(chosen) == len(g.vertices) - 1, "הגרף אינו קשיר ולכן אין לו עץ פורש. הזינו גרף קשיר.")
    return {"tree_edges": chosen, "total_weight": sum(e["weight"] for e in chosen), "steps": steps}


def prim(graph, source=None, **_):
    g = Graph(graph)
    g.undirected()
    source = g.vertices[0] if source is None else g.vertex(source)
    visited, queue, chosen, steps = {source}, [], [], []
    def push(u):
        for v, w, eid in g.adj[u]:
            if v not in visited:
                heapq.heappush(queue, (w, eid, g.index[v], v))
    push(source)
    while queue:
        _, eid, _, v = heapq.heappop(queue)
        if v in visited:
            continue
        visited.add(v)
        chosen.append(g.edges[eid])
        steps.append({"event": "accept", "vertex": v, "edge": g.edges[eid],
                      "selected_edge_ids": [e["id"] for e in chosen]})
        push(v)
    require(len(visited) == len(g.vertices), "הגרף אינו קשיר ולכן אין לו עץ פורש. הזינו גרף קשיר.")
    return {"tree_edges": chosen, "total_weight": sum(e["weight"] for e in chosen), "steps": steps}


def dfs(graph, source=None, **_):
    g = Graph(graph)
    if source is not None:
        g.vertex(source)
    discovery, finish, parent, steps, trees = {}, {}, dict.fromkeys(g.vertices), [], []
    clock = 0
    def visit(u):
        nonlocal clock
        clock += 1
        discovery[u] = clock
        steps.append({"event": "discover", "vertex": u, "time": clock})
        for v, _, eid in g.adj[u]:
            if v not in discovery:
                parent[v] = u
                trees.append(eid)
                visit(v)
        clock += 1
        finish[u] = clock
        steps.append({"event": "finish", "vertex": u, "time": clock})
    roots = ([source] if source else []) + [v for v in g.vertices if v != source]
    for u in roots:
        if u not in discovery:
            visit(u)
    return {"discovery": discovery, "finish": finish, "parents": parent,
            "order": list(discovery), "tree_edge_ids": trees, "steps": steps}


def biconnected(graph, **_):
    g = Graph(graph)
    g.undirected()
    require(all(e["from"] != e["to"] for e in g.edges), "לניתוח רכיבים דו־קשירים יש להזין גרף ללא לולאות עצמיות.")
    discovery, low, articulation, stack, components, steps = {}, {}, set(), [], [], []
    def visit(u, parent_edge=None):
        discovery[u] = low[u] = len(discovery) + 1
        children = 0
        for v, _, eid in g.adj[u]:
            if eid == parent_edge:
                continue
            if v not in discovery:
                children += 1
                stack.append(eid)
                visit(v, eid)
                low[u] = min(low[u], low[v])
                if low[v] >= discovery[u]:
                    if parent_edge is not None or children > 1:
                        articulation.add(u)
                    component = []
                    while stack:
                        top = stack.pop()
                        component.append(top)
                        if top == eid:
                            break
                    components.append(sorted(component))
            elif discovery[v] < discovery[u]:
                stack.append(eid)
                low[u] = min(low[u], discovery[v])
        steps.append({"event": "finish", "vertex": u, "discovery": discovery[u], "low": low[u],
                      "articulation_points": [v for v in g.vertices if v in articulation]})
    for u in g.vertices:
        if u not in discovery:
            visit(u)
    return {"articulation_points": [v for v in g.vertices if v in articulation], "discovery": discovery,
            "low": low, "components": [[g.edges[i] for i in c] for c in components],
            "isolated_vertices": [v for v in g.vertices if not g.adj[v]], "steps": steps,
            "note": "הרכיבים מיוצגים בקשתות; גשר יוצר רכיב בעל קשת אחת. צמתים מבודדים מוצגים בנפרד."}


def max_flow(graph, source, sink, method="edmonds_karp", **_):
    g = Graph(graph)
    require(g.directed, "רשת זרימה חייבת להיות מכוונת (directed: true).")
    g.vertex(source)
    g.vertex(sink)
    require(source != sink, "המקור והיעד חייבים להיות צמתים שונים.")
    require(all(type(e["weight"]) is int and 0 <= e["weight"] <= 50 for e in g.edges),
            "קיבולות הזרימה חייבות להיות מספרים שלמים בין 0 ל־50.")
    require(all(e["from"] != e["to"] for e in g.edges), "רשת זרימה אינה יכולה לכלול לולאות עצמיות.")
    # Separate residual arcs preserve antiparallel ORIGINAL edges correctly.
    residual = {u: [] for u in g.vertices}
    originals = []
    for e in g.edges:
        u, v, cap = e["from"], e["to"], e["weight"]
        forward = {"to": v, "capacity": cap, "reverse": len(residual[v]), "edge_id": e["id"], "direction": 1}
        backward = {"to": u, "capacity": 0, "reverse": len(residual[u]), "edge_id": e["id"], "direction": -1}
        originals.append((u, len(residual[u])))
        residual[u].append(forward)
        residual[v].append(backward)
    total, steps, count = 0, [], 0
    while True:
        parents, frontier = {source: None}, deque([source])
        while frontier and sink not in parents:
            u = frontier.popleft() if method == "edmonds_karp" else frontier.pop()
            for i, edge in enumerate(residual[u]):
                v = edge["to"]
                if edge["capacity"] > 0 and v not in parents:
                    parents[v] = (u, i)
                    frontier.append(v)
        if sink not in parents:
            reachable = set(parents)
            break
        v, path, delta = sink, [], math.inf
        while v != source:
            u, i = parents[v]
            path.append((u, i))
            delta = min(delta, residual[u][i]["capacity"])
            v = u
        path.reverse()
        augmented = []
        for u, i in path:
            edge = residual[u][i]
            edge["capacity"] -= delta
            residual[edge["to"]][edge["reverse"]]["capacity"] += delta
            augmented.append({"from": u, "to": edge["to"], "edge_id": edge["edge_id"], "direction": edge["direction"]})
        total += delta
        count += 1
        if len(steps) < 250:
            steps.append({"event": "augment", "path": [source] + [e["to"] for e in augmented],
                          "arcs": augmented, "bottleneck": delta, "total_flow": total})
    flows = []
    for e, (u, i) in zip(g.edges, originals):
        flows.append({**e, "capacity": e["weight"], "flow": e["weight"] - residual[u][i]["capacity"]})
    cut_edges = [e for e in g.edges if e["from"] in reachable and e["to"] not in reachable]
    return {"max_flow": total, "edge_flows": flows,
            "min_cut": {"source_side": [v for v in g.vertices if v in reachable],
                        "sink_side": [v for v in g.vertices if v not in reachable],
                        "edges": cut_edges, "capacity": sum(e["weight"] for e in cut_edges)},
            "residual": [{"from": u, **edge} for u in g.vertices for edge in residual[u] if edge["capacity"] > 0],
            "steps": steps, "augmentations": count, "trace_truncated": count > len(steps)}


def ford_fulkerson(**kwargs):
    return max_flow(**kwargs, method="ford_fulkerson")


def edmonds_karp(**kwargs):
    return max_flow(**kwargs, method="edmonds_karp")


FUNCTIONS = {fn.__name__: fn for fn in [graph_scan, bfs, dijkstra, bellman_ford, floyd_warshall,
                                       prim, kruskal, union_find, dfs, biconnected, ford_fulkerson, edmonds_karp]}


def execute(name, arguments):
    require(isinstance(name, str) and name in FUNCTIONS, "האלגוריתם המבוקש אינו נתמך.")
    require(isinstance(arguments, dict), "arguments חייב להיות אובייקט JSON.")
    # Validate required parameters before Python dispatch; never execute user code.
    required = ["elements", "operations"] if name == "union_find" else ["graph"]
    if name in ("bfs", "dijkstra", "bellman_ford", "ford_fulkerson", "edmonds_karp"):
        required.append("source")
    if name in ("ford_fulkerson", "edmonds_karp"):
        required.append("sink")
    require(all(k in arguments for k in required), "חסרים שדות חובה: " + ", ".join(k for k in required if k not in arguments))
    allowed = {"elements", "operations"} if name == "union_find" else {"graph", "source", "sink"}
    require(set(arguments) <= allowed, "נשלחו שדות שאינם נתמכים בכלי.")
    return {"algorithm": name, **FUNCTIONS[name](**arguments)}
