"""Common schema shared by all language parsers."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class GraphNode:
    id: str               # unique — "file::symbol" or just "file"
    label: str
    kind: str             # file | class | function | variable | import
    language: str         # python | javascript | typescript | java | c | cpp
    file: str
    line: int = 0
    source_code: str = ""  # D2: embedded for click-to-view; WHY: self-contained HTML (no server); COST: HTML ~5-10× larger; EXIT: replace with fetch("/api/src?id=...") call
    version: str = ""      # D4: version from manifest (requirements.txt/package.json/pom.xml); WHY: conflict detection at a glance; COST: best-effort match only; EXIT: replace with lockfile resolver


@dataclass
class GraphEdge:
    source: str           # node id
    target: str           # node id
    kind: str             # contains | calls | imports | uses


@dataclass
class DependencyGraph:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    def add_node(self, node: GraphNode) -> None:
        if not any(n.id == node.id for n in self.nodes):
            self.nodes.append(node)

    def add_edge(self, edge: GraphEdge) -> None:
        self.edges.append(edge)

    def merge(self, other: "DependencyGraph") -> None:
        for n in other.nodes:
            self.add_node(n)
        self.edges.extend(other.edges)

    def stats(self) -> str:
        kinds = {}
        for n in self.nodes:
            kinds[n.kind] = kinds.get(n.kind, 0) + 1
        edge_kinds = {}
        for e in self.edges:
            edge_kinds[e.kind] = edge_kinds.get(e.kind, 0) + 1
        return (
            f"nodes={len(self.nodes)} {dict(kinds)} | "
            f"edges={len(self.edges)} {dict(edge_kinds)}"
        )
