"""Export DependencyGraph to Obsidian .canvas JSON format."""
import json
import math
from pathlib import Path
from ..common import DependencyGraph

# Obsidian Canvas color codes (string "1"–"6")
_KIND_COLOR = {
    "file": "1",       # red
    "class": "4",      # green
    "function": "3",   # yellow
    "variable": "5",   # pink
    "import": "6",     # purple
}
_KIND_W = {"file": 200, "class": 160, "function": 140, "import": 120, "variable": 100}
_KIND_H = {"file": 60,  "class": 60,  "function": 50,  "import": 40,  "variable": 40}


def _layout(n: int, radius_base: int = 400) -> list[tuple[int, int]]:
    """Spiral layout for n nodes."""
    positions = []
    for i in range(n):
        angle = i * 2.4  # golden angle approx
        r = radius_base + 30 * math.sqrt(i)
        x = int(r * math.cos(angle))
        y = int(r * math.sin(angle))
        positions.append((x, y))
    return positions


class ObsidianCanvasExporter:
    def export(self, g: DependencyGraph, out_path: Path) -> None:
        positions = _layout(len(g.nodes))
        id_map: dict[str, str] = {}

        nodes_json = []
        for i, node in enumerate(g.nodes):
            canvas_id = f"n{i}"
            id_map[node.id] = canvas_id
            x, y = positions[i]
            w = _KIND_W.get(node.kind, 140)
            h = _KIND_H.get(node.kind, 50)
            color = _KIND_COLOR.get(node.kind, "2")
            label = f"[{node.kind}] {node.label}"
            if node.line:
                label += f"\n:{node.line}"
            nodes_json.append({
                "id": canvas_id,
                "type": "text",
                "text": label,
                "x": x - w // 2,
                "y": y - h // 2,
                "width": w,
                "height": h,
                "color": color,
            })

        edges_json = []
        for i, edge in enumerate(g.edges):
            src_id = id_map.get(edge.source)
            tgt_id = id_map.get(edge.target)
            if not src_id or not tgt_id:
                continue
            edges_json.append({
                "id": f"e{i}",
                "fromNode": src_id,
                "fromSide": "right",
                "toNode": tgt_id,
                "toSide": "left",
                "label": edge.kind,
            })

        canvas = {"nodes": nodes_json, "edges": edges_json}
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(canvas, indent=2, ensure_ascii=False))
