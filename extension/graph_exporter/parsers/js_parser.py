"""JS/TS parser using regex (no external deps)."""
import re
from pathlib import Path
from .base import BaseParser
from ..common import DependencyGraph, GraphNode, GraphEdge


def _extract_src(src_lines: list[str], start_line: int, max_lines: int = 120) -> str:
    """Extract function/class body by brace counting from start_line (1-indexed)."""
    depth, started = 0, False
    out = []
    for line in src_lines[start_line - 1: start_line - 1 + max_lines]:
        out.append(line)
        for ch in line:
            if ch == '{':
                depth += 1
                started = True
            elif ch == '}':
                depth -= 1
        if started and depth <= 0:
            break
    return "".join(out)

_FUNC = re.compile(
    r"(?:export\s+)?(?:async\s+)?function\s+(\w+)|"
    r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(",
    re.MULTILINE,
)
_CLASS = re.compile(r"(?:export\s+)?class\s+(\w+)", re.MULTILINE)
_IMPORT = re.compile(
    r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]|'
    r'require\([\'"]([^\'"]+)[\'"]\)',
    re.MULTILINE,
)
_CALL = re.compile(r'(\w+)\s*\(', re.MULTILINE)


class JsParser(BaseParser):
    EXTENSIONS = (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs")

    def parse(self, path: Path) -> DependencyGraph:
        g = DependencyGraph()
        src = path.read_text(encoding="utf-8", errors="replace")
        src_lines = src.splitlines(keepends=True)
        lang = "typescript" if path.suffix in (".ts", ".tsx") else "javascript"
        file_id = str(path)
        g.add_node(GraphNode(id=file_id, label=path.name, kind="file",
                             language=lang, file=file_id))

        for m in _CLASS.finditer(src):
            name = m.group(1)
            cid = f"{file_id}::{name}"
            line = src[: m.start()].count("\n") + 1
            cls_src = _extract_src(src_lines, line)
            g.add_node(GraphNode(id=cid, label=name, kind="class",
                                 language=lang, file=file_id, line=line,
                                 source_code=cls_src))
            g.add_edge(GraphEdge(source=file_id, target=cid, kind="contains"))

        for m in _FUNC.finditer(src):
            name = m.group(1) or m.group(2)
            if not name:
                continue
            fid = f"{file_id}::{name}"
            line = src[: m.start()].count("\n") + 1
            func_src = _extract_src(src_lines, line)
            g.add_node(GraphNode(id=fid, label=name, kind="function",
                                 language=lang, file=file_id, line=line,
                                 source_code=func_src))
            g.add_edge(GraphEdge(source=file_id, target=fid, kind="contains"))

        for m in _IMPORT.finditer(src):
            imp = m.group(1) or m.group(2)
            if not imp:
                continue
            imp_id = f"import::{imp}"
            g.add_node(GraphNode(id=imp_id, label=imp, kind="import",
                                 language=lang, file=file_id))
            g.add_edge(GraphEdge(source=file_id, target=imp_id, kind="imports"))

        # surface-level call extraction
        seen_funcs = {n.label for n in g.nodes if n.kind == "function"}
        for m in _CALL.finditer(src):
            callee = m.group(1)
            if callee in seen_funcs:
                g.add_edge(GraphEdge(source=file_id,
                                     target=f"{file_id}::{callee}",
                                     kind="calls"))

        return g
