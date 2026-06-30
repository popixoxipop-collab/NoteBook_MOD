"""Java parser using regex."""
import re
from pathlib import Path
from .base import BaseParser
from ..common import DependencyGraph, GraphNode, GraphEdge

_CLASS = re.compile(
    r"(?:public|private|protected)?\s*(?:abstract\s+)?(?:class|interface|enum)\s+(\w+)",
    re.MULTILINE,
)
_METHOD = re.compile(
    r"(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\(",
    re.MULTILINE,
)
_IMPORT = re.compile(r"import\s+([\w.]+);", re.MULTILINE)


class JavaParser(BaseParser):
    EXTENSIONS = (".java",)

    def parse(self, path: Path) -> DependencyGraph:
        g = DependencyGraph()
        src = path.read_text(encoding="utf-8", errors="replace")
        file_id = str(path)
        g.add_node(GraphNode(id=file_id, label=path.name, kind="file",
                             language="java", file=file_id))

        for m in _IMPORT.finditer(src):
            imp = m.group(1)
            imp_id = f"import::{imp}"
            g.add_node(GraphNode(id=imp_id, label=imp, kind="import",
                                 language="java", file=file_id))
            g.add_edge(GraphEdge(source=file_id, target=imp_id, kind="imports"))

        for m in _CLASS.finditer(src):
            name = m.group(1)
            cid = f"{file_id}::{name}"
            line = src[: m.start()].count("\n") + 1
            g.add_node(GraphNode(id=cid, label=name, kind="class",
                                 language="java", file=file_id, line=line))
            g.add_edge(GraphEdge(source=file_id, target=cid, kind="contains"))

        skip = {"if", "for", "while", "switch", "catch", "return", "new", "throw"}
        for m in _METHOD.finditer(src):
            name = m.group(1)
            if name in skip:
                continue
            mid = f"{file_id}::{name}"
            line = src[: m.start()].count("\n") + 1
            g.add_node(GraphNode(id=mid, label=name, kind="function",
                                 language="java", file=file_id, line=line))
            g.add_edge(GraphEdge(source=file_id, target=mid, kind="contains"))

        return g
