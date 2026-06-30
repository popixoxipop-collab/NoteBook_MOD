"""CLI entry point: scan a directory and export both Obsidian Canvas + HTML."""
import argparse
import sys
from pathlib import Path
from .common import DependencyGraph
from .parsers import PythonParser, JsParser, JavaParser, CParser
from .exporters import ObsidianCanvasExporter, HtmlPreviewExporter

PARSERS = [PythonParser(), JsParser(), JavaParser(), CParser()]
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "dist", "build", ".tox"}


def scan(root: Path) -> DependencyGraph:
    g = DependencyGraph()
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        for parser in PARSERS:
            if parser.can_parse(path):
                try:
                    sub = parser.parse(path)
                    g.merge(sub)
                except Exception as e:
                    print(f"[warn] {path}: {e}", file=sys.stderr)
                break
    return g


def run() -> None:
    ap = argparse.ArgumentParser(description="NoteBook_MOD dependency graph exporter")
    ap.add_argument("root", nargs="?", default=".", help="root directory to scan")
    ap.add_argument("--out", default="graph_output", help="output directory")
    ap.add_argument("--title", default="NoteBook_MOD", help="graph title")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out  = Path(args.out)

    print(f"Scanning {root} …")
    g = scan(root)
    print(f"  {g.stats()}")

    canvas_path = out / "graph.canvas"
    html_path   = out / "graph.html"
    json_path   = out / "graph.json"

    ObsidianCanvasExporter().export(g, canvas_path)
    HtmlPreviewExporter().export(g, html_path, title=args.title)

    import json
    import dataclasses
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps({
        "nodes": [dataclasses.asdict(n) for n in g.nodes],
        "edges": [dataclasses.asdict(e) for e in g.edges],
    }, indent=2, ensure_ascii=False))

    print(f"  → {canvas_path}  (Obsidian Canvas)")
    print(f"  → {html_path}    (D3 HTML preview)")
    print(f"  → {json_path}    (raw JSON)")


if __name__ == "__main__":
    run()
