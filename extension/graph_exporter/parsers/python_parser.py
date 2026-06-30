"""Python parser using ast stdlib."""
import ast
from pathlib import Path
from .base import BaseParser
from ..common import DependencyGraph, GraphNode, GraphEdge


class PythonParser(BaseParser):
    EXTENSIONS = (".py",)

    def parse(self, path: Path) -> DependencyGraph:
        g = DependencyGraph()
        src = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src, filename=str(path))
        except SyntaxError:
            return g

        file_id = str(path)
        file_node = GraphNode(id=file_id, label=path.name, kind="file",
                              language="python", file=str(path))
        g.add_node(file_node)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nid = f"{file_id}::{node.name}"
                g.add_node(GraphNode(id=nid, label=node.name, kind="function",
                                     language="python", file=str(path),
                                     line=node.lineno))
                g.add_edge(GraphEdge(source=file_id, target=nid, kind="contains"))
                # calls within the function body
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        call_name = self._call_name(child)
                        if call_name:
                            g.add_edge(GraphEdge(source=nid,
                                                 target=f"{file_id}::{call_name}",
                                                 kind="calls"))

            elif isinstance(node, ast.ClassDef):
                cid = f"{file_id}::{node.name}"
                g.add_node(GraphNode(id=cid, label=node.name, kind="class",
                                     language="python", file=str(path),
                                     line=node.lineno))
                g.add_edge(GraphEdge(source=file_id, target=cid, kind="contains"))

            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in (node.names if hasattr(node, "names") else []):
                    imp_label = alias.name
                    imp_id = f"import::{imp_label}"
                    g.add_node(GraphNode(id=imp_id, label=imp_label,
                                        kind="import", language="python",
                                        file=str(path)))
                    g.add_edge(GraphEdge(source=file_id, target=imp_id,
                                        kind="imports"))

        return g

    @staticmethod
    def _call_name(node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None
