"""Export DependencyGraph to a self-contained vis.js hierarchical HTML.

D6: vis.js over D3 custom layout
  WHY: D3 required 200+ lines of manual x/y positioning math that broke on
       graphs with ≠ nodes per tier. vis.js hierarchical UD gives the same
       3-tier mental model (imports top / files mid / symbols bottom) with
       zero positioning code — just level: 0/1/2 on each node.
  COST: CDN dependency vis-network@9.1.6 (~800KB); offline needs local copy.
  EXIT: swap _VIS_CDN with local path; or replace vis.js with cytoscape.js
        if vis.js API changes break the build.
"""
import json
import dataclasses
from pathlib import Path
from ..common import DependencyGraph

_VIS_CDN  = "https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js"
_HLJS_CSS = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css"
_HLJS_JS  = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"

# Apple HIG color palette (matches graphify _generate_better_views.py)
_KIND = {
    "import":   {"shape": "diamond", "bg": "#ff9f0a", "fg": "#fff", "level": 0},
    "file":     {"shape": "box",     "bg": "#0a84ff", "fg": "#fff", "level": 1},
    "class":    {"shape": "ellipse", "bg": "#bf5af2", "fg": "#fff", "level": 2},
    "function": {"shape": "dot",     "bg": "#30d158", "fg": "#fff", "level": 2},
    "variable": {"shape": "dot",     "bg": "#8e8e93", "fg": "#fff", "level": 2},
}
_EDGE_COLOR = {
    "contains": "#3c3c4399",
    "imports":  "#ff9f0a99",
    "calls":    "#30d15899",
    "uses":     "#64d2ff99",
}
_DEFAULT_KIND = {"shape": "dot", "bg": "#636366", "fg": "#fff", "level": 2}

_TEMPLATE = """\
<!doctype html>
<html lang=ko>
<head>
<meta charset=utf-8>
<title>{title} — Dependency Graph</title>
<link rel=stylesheet href="{hljs_css}">
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ height: 100%; font-family: -apple-system, "SF Pro Text", BlinkMacSystemFont, sans-serif; background: #f2f2f7; color: #1c1c1e; }}

/* ── Header ── */
#hd {{
  height: 46px; padding: 0 16px;
  background: rgba(255,255,255,0.88); backdrop-filter: blur(20px);
  border-bottom: 1px solid #d2d2d7;
  display: flex; align-items: center; gap: 12px;
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
}}
#hd-title {{ font-size: 14px; font-weight: 600; }}
#hd-stats {{ font-size: 11px; color: #6e6e73; flex: 1; }}

/* ── Toolbar ── */
#tb {{
  height: 38px; padding: 0 12px;
  background: white; border-bottom: 1px solid #d2d2d7;
  display: flex; align-items: center; gap: 6px;
  position: fixed; top: 46px; left: 0; right: 0; z-index: 99; overflow-x: auto;
}}
#tb-search {{
  height: 24px; padding: 0 8px; border: 1px solid #d2d2d7; border-radius: 7px;
  font-size: 12px; width: 180px; outline: none; background: #f2f2f7; flex-shrink: 0;
}}
#tb-search:focus {{ border-color: #0a84ff; background: white; }}
.sep {{ width: 1px; height: 18px; background: #d2d2d7; margin: 0 2px; flex-shrink: 0; }}
.kbtn {{
  height: 24px; padding: 0 8px; border-radius: 7px; border: 1.5px solid transparent;
  font-size: 11px; cursor: pointer; font-weight: 500; white-space: nowrap; flex-shrink: 0;
  transition: opacity 0.15s;
}}
.kbtn.on {{ opacity: 1; border-color: currentColor; }}
.kbtn.off {{ opacity: 0.4; }}
.kbtn[data-k=import]   {{ color: #ff9f0a; background: #fff8ec; }}
.kbtn[data-k=file]     {{ color: #0a84ff; background: #ecf4ff; }}
.kbtn[data-k=function] {{ color: #30d158; background: #edfaf2; }}
.kbtn[data-k=class]    {{ color: #bf5af2; background: #f8ecff; }}
.ebtn {{
  height: 24px; padding: 0 8px; border-radius: 7px; border: 1px solid #d2d2d7;
  font-size: 11px; cursor: pointer; background: white; color: #3c3c43;
  white-space: nowrap; flex-shrink: 0; transition: background 0.15s;
}}
.ebtn.off {{ background: #f2f2f7; color: #aeaeb2; }}

/* ── Main ── */
#main {{ position: fixed; top: 84px; left: 0; right: 0; bottom: 0; display: flex; }}
#gw {{ flex: 1; position: relative; min-width: 0; }}
#net {{ width: 100%; height: 100%; }}

/* ── Legend ── */
#leg {{
  position: absolute; bottom: 14px; left: 14px;
  background: rgba(255,255,255,0.9); backdrop-filter: blur(10px);
  border: 1px solid #d2d2d7; border-radius: 10px; padding: 9px 12px; font-size: 11px;
}}
#leg .row {{ display: flex; align-items: center; gap: 6px; margin: 3px 0; color: #3c3c43; }}
.sym-dia {{ width: 10px; height: 10px; transform: rotate(45deg); display: inline-block; flex-shrink: 0; border-radius: 1px; }}
.sym-box {{ width: 12px; height: 8px; border-radius: 2px; display: inline-block; flex-shrink: 0; }}
.sym-dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; flex-shrink: 0; }}
.sym-ell {{ width: 14px; height: 9px; border-radius: 50%; display: inline-block; flex-shrink: 0; }}

/* ── Code panel ── */
#cp {{
  width: 0; overflow: hidden; transition: width 0.22s ease;
  background: white; border-left: 1px solid #d2d2d7;
  display: flex; flex-direction: column;
}}
#cp.open {{ width: 440px; }}
#cp-hd {{
  padding: 11px 14px; border-bottom: 1px solid #d2d2d7;
  display: flex; justify-content: space-between; align-items: flex-start;
  flex-shrink: 0;
}}
#cp-name {{ font-size: 13px; font-weight: 600; }}
#cp-meta {{ font-size: 11px; color: #6e6e73; margin-top: 2px; }}
#cp-close {{
  cursor: pointer; width: 22px; height: 22px; font-size: 15px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%; background: #f2f2f7; color: #8e8e93; margin-left: 8px;
}}
#cp-close:hover {{ background: #d2d2d7; color: #1c1c1e; }}
#cp-body {{ flex: 1; overflow: auto; }}
#cp-body pre {{ margin: 0; font-size: 12px; line-height: 1.55; border-radius: 0; }}
#cp-body code {{ font-family: "SF Mono", Menlo, Monaco, Consolas, monospace; }}
#cp-empty {{
  padding: 32px 20px; color: #8e8e93; font-size: 13px; line-height: 1.7; text-align: center;
}}
</style>
</head>
<body>

<div id=hd>
  <span id=hd-title>{title}</span>
  <span id=hd-stats>{stats}</span>
</div>

<div id=tb>
  <input id=tb-search type=text placeholder="노드 검색…">
  <div class=sep></div>
  <button class="kbtn on" data-k=import>◆ 외부의존성</button>
  <button class="kbtn on" data-k=file>▪ 파일</button>
  <button class="kbtn on" data-k=function>● 함수</button>
  <button class="kbtn on" data-k=class>◎ 클래스</button>
  <div class=sep></div>
  <button class="ebtn on" data-ek=contains>contains</button>
  <button class="ebtn on" data-ek=imports>imports</button>
  <button class="ebtn on" data-ek=calls>calls</button>
</div>

<div id=main>
  <div id=gw>
    <div id=net></div>
    <div id=leg>
      <div class=row><span class=sym-dia style="background:#ff9f0a"></span>외부 의존성</div>
      <div class=row><span class=sym-box style="background:#0a84ff"></span>파일</div>
      <div class=row><span class=sym-ell style="background:#bf5af2"></span>클래스</div>
      <div class=row><span class=sym-dot style="background:#30d158"></span>함수</div>
    </div>
  </div>
  <div id=cp>
    <div id=cp-hd>
      <div><div id=cp-name></div><div id=cp-meta></div></div>
      <div id=cp-close>×</div>
    </div>
    <div id=cp-body><div id=cp-empty>← 함수 ● 또는 클래스 ◎ 노드를 클릭하면<br>소스코드가 여기에 표시됩니다</div></div>
  </div>
</div>

<script src="{vis_cdn}"></script>
<script src="{hljs_js}"></script>
<script>
/* ── raw data ── */
const VIS_NODES = {vis_nodes};
const VIS_EDGES = {vis_edges};
const META      = {meta_json};  /* id → {{label, file, line, language, source_code, kind}} */

/* ── state ── */
const hiddenKinds = new Set();
const hiddenEKinds = new Set();
let searchQ = '';

/* ── vis.js datasets ── */
const nodesDS = new vis.DataSet(VIS_NODES);
const edgesDS = new vis.DataSet(VIS_EDGES);

const net = new vis.Network(
  document.getElementById('net'),
  {{ nodes: nodesDS, edges: edgesDS }},
  {{
    layout: {{
      hierarchical: {{
        enabled: true,
        direction: 'UD',
        sortMethod: 'directed',
        levelSeparation: 170,
        nodeSpacing: 130,
        treeSpacing: 210,
        blockShifting: true,
        edgeMinimization: true,
        parentCentralization: true,
      }},
    }},
    physics: {{ enabled: false }},
    nodes: {{
      scaling: {{ min: 8, max: 36, label: {{ enabled: true, min: 10, max: 16 }} }},
      borderWidth: 0,
      shadow: {{ enabled: true, size: 3, color: 'rgba(0,0,0,0.07)' }},
    }},
    edges: {{
      smooth: {{ type: 'cubicBezier', forceDirection: 'vertical', roundness: 0.42 }},
      width: 0.7,
      selectionWidth: 2.8,
      font: {{ size: 9, color: '#6e6e73', strokeWidth: 2, strokeColor: '#fff' }},
    }},
    interaction: {{
      hover: true, tooltipDelay: 160,
      navigationButtons: true, keyboard: true,
      zoomView: true, dragView: true,
    }},
  }}
);

/* ── click → code panel ── */
net.on('click', p => {{
  if (!p.nodes.length) return;
  const m = META[p.nodes[0]];
  if (!m || !m.source_code) return;
  openPanel(m);
}});

function openPanel(m) {{
  document.getElementById('cp-name').textContent = m.label;
  const file = m.file ? m.file.split('/').pop() : '';
  const parts = [m.kind, file, m.line ? 'L' + m.line : ''].filter(Boolean);
  document.getElementById('cp-meta').textContent = parts.join('  ·  ');
  const body = document.getElementById('cp-body');
  const lang = ({{python:'python', javascript:'javascript', typescript:'typescript',
                   java:'java', c:'cpp', cpp:'cpp'}})[m.language] || 'plaintext';
  let hi;
  try {{ hi = hljs.highlight(m.source_code, {{language: lang}}).value; }}
  catch(e) {{ hi = m.source_code.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }}
  body.innerHTML = '<pre><code class="hljs language-' + lang + '">' + hi + '</code></pre>';
  document.getElementById('cp').classList.add('open');
}}

document.getElementById('cp-close').onclick = () => {{
  document.getElementById('cp').classList.remove('open');
}};

/* ── search ── */
document.getElementById('tb-search').oninput = function() {{
  searchQ = this.value.toLowerCase();
  applyFilters();
}};

/* ── kind filter ── */
document.querySelectorAll('.kbtn').forEach(btn => {{
  btn.onclick = function() {{
    const k = this.dataset.k;
    this.classList.toggle('on');
    this.classList.toggle('off');
    if (hiddenKinds.has(k)) hiddenKinds.delete(k); else hiddenKinds.add(k);
    applyFilters();
  }};
}});

/* ── edge kind filter ── */
document.querySelectorAll('.ebtn').forEach(btn => {{
  btn.onclick = function() {{
    const k = this.dataset.ek;
    this.classList.toggle('on');
    this.classList.toggle('off');
    if (hiddenEKinds.has(k)) hiddenEKinds.delete(k); else hiddenEKinds.add(k);
    applyEdgeFilters();
  }};
}});

function applyFilters() {{
  const updates = VIS_NODES.map(n => {{
    const kindHide = hiddenKinds.has(n._kind);
    const searchHide = searchQ && !n._fullLabel.toLowerCase().includes(searchQ);
    return {{ id: n.id, hidden: kindHide || searchHide }};
  }});
  nodesDS.update(updates);
}}

function applyEdgeFilters() {{
  edgesDS.update(VIS_EDGES.map(e => ({{ id: e.id, hidden: hiddenEKinds.has(e._kind) }})));
}}
</script>
</body>
</html>
"""


def _truncate(s: str, n: int) -> str:
    return s[:n - 1] + "…" if len(s) > n else s


class HtmlPreviewExporter:
    def export(self, g: DependencyGraph, out_path: Path, title: str = "NoteBook_MOD") -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # ── degree map (fan-in + fan-out) ──
        degree: dict[str, int] = {}
        for e in g.edges:
            degree[e.source] = degree.get(e.source, 0) + 1
            degree[e.target] = degree.get(e.target, 0) + 1

        # ── vis.js nodes (display-only, no source_code) ──
        vis_nodes: list[dict] = []
        meta: dict[str, dict] = {}

        for n in g.nodes:
            cfg = _KIND.get(n.kind, _DEFAULT_KIND)
            short = _truncate(n.label, 28)
            ver_line = f"\n[{n.version}]" if n.version else ""
            tip_parts = [f"{n.kind}: {n.label}"]
            if n.file:
                tip_parts.append(Path(n.file).name + (f":{n.line}" if n.line else ""))
            if n.version:
                tip_parts.append(f"ver: {n.version}")

            vis_nodes.append({
                "id": n.id,
                "label": short + ver_line,
                "title": "\n".join(tip_parts),
                "shape": cfg["shape"],
                "color": {
                    "background": cfg["bg"],
                    "border": cfg["bg"],
                    "highlight": {"background": cfg["bg"], "border": "#fff"},
                    "hover": {"background": cfg["bg"], "border": "#fff"},
                },
                "font": {"color": cfg["fg"], "size": 11},
                "level": cfg["level"],
                "value": max(degree.get(n.id, 0), 1),
                "_kind": n.kind,
                "_fullLabel": n.label,
            })

            meta[n.id] = {
                "label": n.label,
                "file": n.file or "",
                "line": n.line,
                "language": n.language or "",
                "source_code": n.source_code or "",
                "kind": n.kind,
            }

        # ── vis.js edges ──
        vis_edges: list[dict] = []
        for e in g.edges:
            color = _EDGE_COLOR.get(e.kind, "#8e8e9399")
            vis_edges.append({
                "id": f"{e.source}|{e.target}|{e.kind}",
                "from": e.source,
                "to": e.target,
                "color": {"color": color, "highlight": color, "hover": color},
                "arrows": {"to": {"enabled": True, "scaleFactor": 0.4}},
                "_kind": e.kind,
                "hidden": False,
            })

        # ── stats bar ──
        counts: dict[str, int] = {}
        for n in g.nodes:
            counts[n.kind] = counts.get(n.kind, 0) + 1
        versioned = sum(1 for n in g.nodes if n.kind == "import" and n.version)
        stats = (
            f"{counts.get('file', 0)} 파일  "
            f"{counts.get('function', 0)} 함수  "
            f"{counts.get('class', 0)} 클래스  "
            f"{counts.get('import', 0)} 외부의존성"
            + (f" ({versioned}개 버전명시)" if versioned else "")
            + f"  |  {len(g.edges)} 엣지"
        )

        html = _TEMPLATE.format(
            title=title,
            stats=stats,
            vis_cdn=_VIS_CDN,
            hljs_css=_HLJS_CSS,
            hljs_js=_HLJS_JS,
            vis_nodes=json.dumps(vis_nodes, ensure_ascii=False),
            vis_edges=json.dumps(vis_edges, ensure_ascii=False),
            meta_json=json.dumps(meta, ensure_ascii=False),
        )
        out_path.write_text(html, encoding="utf-8")
