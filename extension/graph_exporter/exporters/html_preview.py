"""Export DependencyGraph to a self-contained D3.js force-graph HTML."""
import json
from pathlib import Path
from ..common import DependencyGraph

_KIND_COLOR = {
    "file": "#3b82f6",
    "class": "#22c55e",
    "function": "#f59e0b",
    "import": "#a855f7",
    "variable": "#ec4899",
}

_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Dependency Graph — {title}</title>
<style>
  body {{ margin:0; background:#0d1117; color:#e2e8f0; font-family:monospace; }}
  #info {{ position:fixed; top:12px; left:12px; font-size:12px; color:#64748b; }}
  #legend {{ position:fixed; top:12px; right:12px; font-size:12px; }}
  .legend-item {{ display:flex; align-items:center; gap:6px; margin-bottom:4px; }}
  .dot {{ width:10px; height:10px; border-radius:50%; }}
  svg {{ width:100vw; height:100vh; }}
  .link {{ stroke:#334155; stroke-opacity:0.6; }}
  .node circle {{ stroke:#0d1117; stroke-width:1.5px; cursor:pointer; }}
  .label {{ font-size:10px; fill:#94a3b8; pointer-events:none; }}
  .tooltip {{
    position:fixed; background:#1e293b; border:1px solid #334155;
    border-radius:6px; padding:8px 12px; font-size:12px; pointer-events:none;
    opacity:0; transition:opacity .15s;
  }}
</style>
</head>
<body>
<div id="info">nodes: {n_nodes} | edges: {n_edges}</div>
<div id="legend">{legend_html}</div>
<div class="tooltip" id="tip"></div>
<svg id="graph"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const GRAPH = {graph_json};
const COLOR = {color_json};

const svg = d3.select("#graph");
const W = window.innerWidth, H = window.innerHeight;
svg.attr("viewBox", [0,0,W,H]);

const g = svg.append("g");
svg.call(d3.zoom().on("zoom", e => g.attr("transform", e.transform)));

const sim = d3.forceSimulation(GRAPH.nodes)
  .force("link", d3.forceLink(GRAPH.links).id(d=>d.id).distance(80))
  .force("charge", d3.forceManyBody().strength(-120))
  .force("center", d3.forceCenter(W/2, H/2))
  .force("collision", d3.forceCollide(20));

const link = g.append("g")
  .selectAll("line")
  .data(GRAPH.links)
  .join("line")
  .attr("class","link")
  .attr("marker-end", "url(#arrow)");

svg.append("defs").append("marker")
  .attr("id","arrow").attr("viewBox","0 -5 10 10")
  .attr("refX",18).attr("refY",0)
  .attr("markerWidth",6).attr("markerHeight",6)
  .attr("orient","auto")
  .append("path").attr("d","M0,-5L10,0L0,5").attr("fill","#334155");

const tip = document.getElementById("tip");
const node = g.append("g")
  .selectAll("g")
  .data(GRAPH.nodes)
  .join("g")
  .call(d3.drag()
    .on("start", (e,d) => {{ if(!e.active) sim.alphaTarget(.3).restart(); d.fx=d.x; d.fy=d.y; }})
    .on("drag",  (e,d) => {{ d.fx=e.x; d.fy=e.y; }})
    .on("end",   (e,d) => {{ if(!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }}))
  .on("mouseover", (e,d) => {{
    tip.style.opacity=1;
    tip.innerHTML = `<b>${{d.label}}</b><br/>${{d.kind}} · ${{d.language}}<br/>${{d.file}}${{d.line?":"+d.line:""}}`;
  }})
  .on("mousemove", e => {{ tip.style.left=(e.clientX+14)+"px"; tip.style.top=(e.clientY-10)+"px"; }})
  .on("mouseout",  () => {{ tip.style.opacity=0; }});

node.append("circle")
  .attr("r", d => d.kind==="file"?10:d.kind==="class"?8:6)
  .attr("fill", d => COLOR[d.kind]||"#64748b");

node.append("text")
  .attr("class","label")
  .attr("x",13).attr("y",4)
  .text(d => d.label.length>20?d.label.slice(0,18)+"…":d.label);

sim.on("tick", () => {{
  link.attr("x1",d=>d.source.x).attr("y1",d=>d.source.y)
      .attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);
  node.attr("transform",d=>`translate(${{d.x}},${{d.y}})`);
}});
</script>
</body>
</html>
"""


class HtmlPreviewExporter:
    def export(self, g: DependencyGraph, out_path: Path, title: str = "NoteBook_MOD") -> None:
        node_ids = {n.id for n in g.nodes}
        nodes_d3 = [
            {"id": n.id, "label": n.label, "kind": n.kind,
             "language": n.language, "file": n.file, "line": n.line}
            for n in g.nodes
        ]
        links_d3 = [
            {"source": e.source, "target": e.target, "kind": e.kind}
            for e in g.edges
            if e.source in node_ids and e.target in node_ids
        ]

        legend_items = "".join(
            f'<div class="legend-item"><div class="dot" style="background:{c}"></div>{k}</div>'
            for k, c in _KIND_COLOR.items()
        )

        html = _TEMPLATE.format(
            title=title,
            n_nodes=len(nodes_d3),
            n_edges=len(links_d3),
            legend_html=legend_items,
            graph_json=json.dumps({"nodes": nodes_d3, "links": links_d3}),
            color_json=json.dumps(_KIND_COLOR),
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
