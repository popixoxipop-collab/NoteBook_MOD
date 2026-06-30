"""C / C++ parser using regex."""
import re
from pathlib import Path
from .base import BaseParser
from ..common import DependencyGraph, GraphNode, GraphEdge

_INCLUDE = re.compile(r'#include\s+[<"]([^>"]+)[>"]', re.MULTILINE)
_FUNC = re.compile(
    r"^[\w\s\*&:<>]+\s+(\w+)\s*\([^)]*\)\s*(?:const\s*)?\{",
    re.MULTILINE,
)
_CLASS = re.compile(r"(?:class|struct)\s+(\w+)\s*[:{]", re.MULTILINE)
_SKIP = {"if", "for", "while", "switch", "do", "else", "try", "catch", "main"}


class CParser(BaseParser):
    EXTENSIONS = (".c", ".cpp", ".cc", ".cxx", ".h", ".hpp")

    def parse(self, path: Path) -> DependencyGraph:
        g = DependencyGraph()
        src = path.read_text(encoding="utf-8", errors="replace")
        lang = "cpp" if path.suffix in (".cpp", ".cc", ".cxx", ".hpp") else "c"
        file_id = str(path)
        g.add_node(GraphNode(id=file_id, label=path.name, kind="file",
                             language=lang, file=file_id))

        for m in _INCLUDE.finditer(src):
            inc = m.group(1)
            inc_id = f"include::{inc}"
            g.add_node(GraphNode(id=inc_id, label=inc, kind="import",
                                 language=lang, file=file_id))
            g.add_edge(GraphEdge(source=file_id, target=inc_id, kind="imports"))

        for m in _CLASS.finditer(src):
            name = m.group(1)
            if name in _SKIP:
                continue
            cid = f"{file_id}::{name}"
            line = src[: m.start()].count("\n") + 1
            g.add_node(GraphNode(id=cid, label=name, kind="class",
                                 language=lang, file=file_id, line=line))
            g.add_edge(GraphEdge(source=file_id, target=cid, kind="contains"))

        for m in _FUNC.finditer(src):
            name = m.group(1)
            if name in _SKIP:
                continue
            fid = f"{file_id}::{name}"
            line = src[: m.start()].count("\n") + 1
            g.add_node(GraphNode(id=fid, label=name, kind="function",
                                 language=lang, file=file_id, line=line))
            g.add_edge(GraphEdge(source=file_id, target=fid, kind="contains"))

        return g
