"""CLI entry point: scan a directory and export both Obsidian Canvas + HTML.

Usage:
  python -m graph_exporter.cli [root] [--out DIR]   # scan + export (default)
  python -m graph_exporter.cli query "TERMS" [--out DIR] [-k N]  # search graph.json

D1: post-scan call resolution
  WHY: Python parser emits calls edges as "{file}::{name}" (intra-file only).
       Cross-file calls miss unless we do a second pass mapping by symbol name.
  COST: Ambiguous names (multiple files define same func) get fan-out edges.
  EXIT: swap for a proper import-graph resolver that tracks `from X import Y` paths.
"""
import argparse
import sys
from pathlib import Path
from .common import DependencyGraph, GraphEdge
from .parsers import PythonParser, JsParser, JavaParser, CParser
from .exporters import ObsidianCanvasExporter, HtmlPreviewExporter
from .version_resolver import annotate_graph
from .query import search as graph_search

PARSERS = [PythonParser(), JsParser(), JavaParser(), CParser()]
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "dist", "build", ".tox"}


def resolve_calls(g: DependencyGraph) -> None:
    """Second pass: fix cross-file call edges that point to non-existent nodes."""
    node_ids = {n.id for n in g.nodes}
    name_to_ids: dict[str, list[str]] = {}
    for n in g.nodes:
        if n.kind in ("function", "class"):
            name_to_ids.setdefault(n.label, []).append(n.id)

    resolved: list[GraphEdge] = []
    for e in g.edges:
        if e.kind == "calls" and e.target not in node_ids:
            call_name = e.target.split("::")[-1] if "::" in e.target else e.target
            matches = name_to_ids.get(call_name, [])
            for mid in matches:
                if mid != e.source:  # skip self-loop
                    resolved.append(GraphEdge(source=e.source, target=mid, kind="calls"))
        else:
            resolved.append(e)
    g.edges = resolved


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


def _run_query(argv: list[str]) -> None:
    ap = argparse.ArgumentParser(prog="graph_exporter query")
    ap.add_argument("terms", nargs="+", help="search terms")
    ap.add_argument("--out", default="graph_output", help="directory containing graph.json")
    ap.add_argument("-k", "--top-k", type=int, default=20, help="max nodes to return")
    args = ap.parse_args(argv)

    graph_json = Path(args.out) / "graph.json"
    if not graph_json.exists():
        print(f"[error] {graph_json} not found — run scan first", file=sys.stderr)
        sys.exit(1)

    query = " ".join(args.terms)
    print(graph_search(graph_json, query, top_k=args.top_k))


def run() -> None:
    # Dispatch: "query" as first arg → search mode; otherwise → scan+export (backward compat)
    if len(sys.argv) > 1 and sys.argv[1] == "query":
        _run_query(sys.argv[2:])
        return

    ap = argparse.ArgumentParser(description="NoteBook_MOD dependency graph exporter")
    ap.add_argument("root", nargs="?", default=".", help="root directory to scan")
    ap.add_argument("--out", default="graph_output", help="output directory")
    ap.add_argument("--title", default="NoteBook_MOD", help="graph title")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out  = Path(args.out)

    print(f"Scanning {root} …")
    g = scan(root)
    print(f"  pre-resolve:  {g.stats()}")
    resolve_calls(g)
    print(f"  post-resolve: {g.stats()}")
    annotate_graph(g, root)

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
    print(f"  → {html_path}    (vis.js hierarchical HTML)")
    print(f"  → {json_path}    (raw JSON)")


if __name__ == "__main__":
    run()
