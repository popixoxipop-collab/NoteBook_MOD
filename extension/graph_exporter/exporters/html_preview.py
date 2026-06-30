"""Export DependencyGraph to a self-contained layered HTML.

D3: layered layout (file→symbol→import, top-down)
  WHY: mental model of project = files at top, symbols in middle, deps at bottom.
       Force layout buried this hierarchy; layered makes file ownership obvious.
  COST: cross-file call edges can be hard to trace visually (long arcs).
  EXIT: replace _LAYOUT_JS block with force layout; keep rest of template unchanged.
"""
import json
import dataclasses
from pathlib import Path
from ..common import DependencyGraph

_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>{title} — 의존성 그래프</title>
<link rel="stylesheet"
  href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{display:flex;height:100vh;background:#0d1117;color:#e2e8f0;font-family:-apple-system,ui-monospace,monospace;overflow:hidden}}

/* ── LEFT: graph panel ── */
#gp{{flex:1;position:relative;overflow:hidden;min-width:0}}
#gp svg{{width:100%;height:100%;display:block}}

/* ── RIGHT: code panel ── */
#cp{{width:420px;min-width:340px;background:#161b22;border-left:1px solid #21262d;display:flex;flex-direction:column;transition:width .2s}}
#cp.hidden{{width:0;min-width:0;overflow:hidden;border:none}}
#ch{{padding:12px 14px 10px;border-bottom:1px solid #21262d;display:flex;align-items:flex-start;gap:8px;min-height:52px}}
#ch-info{{flex:1;min-width:0}}
#ch-name{{font-size:13px;font-weight:700;color:#e2e8f0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
#ch-meta{{font-size:11px;color:#64748b;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
#cb{{flex:1;overflow-y:auto}}
#cb pre{{margin:0}}
#cb code{{font-size:12px;line-height:1.65;padding:16px!important;display:block}}
.placeholder{{display:flex;align-items:center;justify-content:center;height:100%;color:#374151;font-size:13px;text-align:center;padding:24px;line-height:1.7}}
#close-btn{{background:none;border:none;color:#64748b;cursor:pointer;font-size:18px;padding:2px 4px;flex-shrink:0;line-height:1}}
#close-btn:hover{{color:#e2e8f0}}

/* ── overlay labels ── */
#stats{{position:absolute;top:10px;left:12px;font-size:11px;color:#4b5563;background:rgba(13,17,23,.85);padding:5px 10px;border-radius:4px;pointer-events:none}}
#legend{{position:absolute;top:10px;right:12px;font-size:11px;background:rgba(13,17,23,.85);padding:8px 12px;border-radius:4px}}
.lr{{display:flex;align-items:center;gap:6px;margin-bottom:4px}}
.ld{{width:10px;height:10px;border-radius:2px;flex-shrink:0}}
#hint{{position:absolute;bottom:10px;left:50%;transform:translateX(-50%);font-size:11px;color:#374151;pointer-events:none;white-space:nowrap}}

/* ── node styles ── */
.n-file rect{{fill:#1e3a5f;stroke:#3b82f6;stroke-width:1.5px;rx:6px}}
.n-file text{{fill:#93c5fd;font-size:12px;font-weight:600;pointer-events:none}}
.n-function rect{{fill:#1c2a1c;stroke:#22c55e;stroke-width:1px}}
.n-function text{{fill:#86efac;font-size:11px;pointer-events:none}}
.n-class rect{{fill:#1c2340;stroke:#818cf8;stroke-width:1px}}
.n-class text{{fill:#c4b5fd;font-size:11px;pointer-events:none}}
.n-import rect{{fill:#1a1a1a;stroke:#404040;stroke-width:1px}}
.n-import text{{fill:#71717a;font-size:10px;pointer-events:none}}
.n-function,.n-class{{cursor:pointer}}
.n-function:hover rect,.n-class:hover rect{{stroke-width:2px;filter:brightness(1.3)}}
.n-function.sel rect{{stroke:#4ade80;stroke-width:2.5px;fill:#243524}}
.n-class.sel rect{{stroke:#a78bfa;stroke-width:2.5px;fill:#1e2240}}

/* ── edge styles ── */
.e-contains{{stroke:#1e3a5f;stroke-width:1px;opacity:.5;fill:none}}
.e-imports{{stroke:#1d4ed8;stroke-width:1px;stroke-dasharray:4 2;opacity:.35;fill:none}}
.e-calls{{stroke:#92400e;stroke-width:1px;opacity:.3;fill:none;marker-end:url(#arrow-calls)}}
</style>
</head>
<body>
<div id="gp">
  <div id="stats"></div>
  <div id="legend">
    <div class="lr"><div class="ld" style="background:#3b82f6"></div>파일</div>
    <div class="lr"><div class="ld" style="background:#22c55e"></div>함수</div>
    <div class="lr"><div class="ld" style="background:#818cf8"></div>클래스</div>
    <div class="lr"><div class="ld" style="background:#404040"></div>외부 import</div>
    <div class="lr" style="margin-top:6px;border-top:1px solid #21262d;padding-top:6px">
      <div class="ld" style="background:#1e3a5f;border:1px solid #3b82f6"></div><span style="color:#4b5563">── contains</span>
    </div>
    <div class="lr"><div class="ld" style="background:#92400e"></div><span style="color:#4b5563">── calls</span></div>
    <div class="lr"><div class="ld" style="background:#1d4ed8"></div><span style="color:#4b5563">--- imports</span></div>
  </div>
  <div id="hint">스크롤: 줌 · 드래그: 이동 · 함수/클래스 클릭: 소스보기</div>
  <svg id="graph">
    <defs>
      <marker id="arrow-calls" viewBox="0 -4 8 8" refX="16" refY="0"
        markerWidth="6" markerHeight="6" orient="auto">
        <path d="M0,-4L8,0L0,4" fill="#92400e" opacity=".6"/>
      </marker>
    </defs>
  </svg>
</div>
<div id="cp">
  <div id="ch">
    <div id="ch-info">
      <div id="ch-name" style="color:#4b5563">클릭하면 소스코드 표시</div>
      <div id="ch-meta"></div>
    </div>
    <button id="close-btn" onclick="closePanel()" title="닫기">×</button>
  </div>
  <div id="cb">
    <div class="placeholder">← 그래프에서<br>함수 <span style="color:#86efac">●</span> 또는 클래스 <span style="color:#c4b5fd">●</span> 노드를<br>클릭하면 소스코드가 여기에 표시됩니다</div>
  </div>
</div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script>
/* ═══════════════════════════════════════════════
   DATA
═══════════════════════════════════════════════ */
const GRAPH = {graph_json};
const nodeById = Object.fromEntries(GRAPH.nodes.map(n => [n.id, n]));

/* ═══════════════════════════════════════════════
   LAYOUT CONSTANTS
   D3: top-down layered
     WHY: matches mental model; file→symbol→import reads like package hierarchy
     COST: call arcs can be wide if callee is in a distant file column
     EXIT: change only this block; rest of render code is layout-agnostic
═══════════════════════════════════════════════ */
const FILE_Y   = 70;
const SYM_Y0   = 195;   // top of symbol layer
const SYM_ROW  = 55;    // row height within file column
const SYM_COLS = 2;     // max columns per file group
const NODE_W   = 148;   // symbol node width
const NODE_H   = 42;    // symbol node height
const FILE_W   = 170;   // file node width
const FILE_H   = 40;    // file node height
const IMP_W    = 112;   // import node width
const IMP_H    = 32;    // import node height
const PAD      = 50;    // left/right padding
const COL_GAP  = 18;    // gap between file columns

/* partition nodes */
const fileNodes = GRAPH.nodes.filter(n => n.kind === 'file');
const symNodes  = GRAPH.nodes.filter(n => n.kind === 'function' || n.kind === 'class');
const impNodes  = GRAPH.nodes.filter(n => n.kind === 'import');

/* file → children map (from 'contains' edges) */
const childMap = {{}};
fileNodes.forEach(f => childMap[f.id] = []);
GRAPH.edges.forEach(e => {{
  if (e.kind === 'contains' && childMap[e.source] !== undefined) {{
    const child = nodeById[e.target];
    if (child) childMap[e.source].push(child);
  }}
}});
Object.values(childMap).forEach(arr => arr.sort((a,b) => a.line - b.line));

/* Compute column width per file (based on child count) */
function colWidth(fileId) {{
  const n = childMap[fileId].length;
  const cols = Math.min(SYM_COLS, n || 1);
  return Math.max(cols * (NODE_W + 8) + 24, FILE_W + 24);
}}

/* assign x positions for file nodes */
let cx = PAD;
fileNodes.forEach(f => {{
  const cw = colWidth(f.id);
  f.x = cx + cw / 2;
  f.y = FILE_Y;
  f._cw = cw;  // store column width
  cx += cw + COL_GAP;
}});
const TOTAL_W = cx + PAD;

/* assign positions for symbol nodes within each file column */
let maxSymY = SYM_Y0;
fileNodes.forEach(f => {{
  const children = childMap[f.id];
  const cols = Math.min(SYM_COLS, children.length || 1);
  const cellW = NODE_W + 8;
  const groupW = cols * cellW;
  children.forEach((child, i) => {{
    const row = Math.floor(i / cols);
    const col = i % cols;
    child.x = f.x - groupW/2 + col * cellW + NODE_W/2;
    child.y = SYM_Y0 + row * SYM_ROW;
    if (child.y > maxSymY) maxSymY = child.y;
  }});
}});

/* symbols with no file parent */
symNodes.filter(n => n.x === undefined).forEach((n, i) => {{
  n.x = PAD + i * (NODE_W + 10);
  n.y = maxSymY;
}});

/* import nodes: fill full width at bottom */
const IMP_Y0 = maxSymY + NODE_H/2 + 90;
const IMP_COLS = Math.max(1, Math.floor((TOTAL_W - PAD*2) / (IMP_W + 6)));
const IMP_ROW_H = IMP_H + 8;
impNodes.forEach((n, i) => {{
  const row = Math.floor(i / IMP_COLS);
  const col = i % IMP_COLS;
  n.x = PAD + col * (IMP_W + 6) + IMP_W/2;
  n.y = IMP_Y0 + row * IMP_ROW_H;
}});
const IMP_ROWS = Math.ceil(impNodes.length / IMP_COLS);
const TOTAL_H = IMP_Y0 + IMP_ROWS * IMP_ROW_H + 60;

/* ═══════════════════════════════════════════════
   SVG SETUP
═══════════════════════════════════════════════ */
const svg = d3.select('#graph')
  .attr('viewBox', `0 0 ${{TOTAL_W}} ${{TOTAL_H}}`)
  .attr('preserveAspectRatio','xMinYMin meet');

const g = svg.append('g');
svg.call(d3.zoom().scaleExtent([0.15, 5])
  .on('zoom', e => g.attr('transform', e.transform)));

/* ═══════════════════════════════════════════════
   EDGES (drawn before nodes so they appear underneath)
═══════════════════════════════════════════════ */
const edgeG = g.append('g').attr('class','edges');

GRAPH.edges.forEach(e => {{
  const s = nodeById[e.source], t = nodeById[e.target];
  if (!s || !t || s.x === undefined || t.x === undefined) return;

  if (e.kind === 'contains') {{
    /* straight line file→symbol */
    edgeG.append('line')
      .attr('class','e-contains')
      .attr('x1', s.x).attr('y1', s.y + FILE_H/2 + 2)
      .attr('x2', t.x).attr('y2', t.y - NODE_H/2 - 2);
    return;
  }}

  if (e.kind === 'imports') {{
    /* curved dashed arc to import node */
    const mx = (s.x + t.x) / 2;
    const my = Math.max(s.y, t.y) + 40;
    edgeG.append('path')
      .attr('class','e-imports')
      .attr('d', `M${{s.x}},${{s.y + FILE_H/2}} Q${{mx}},${{my}} ${{t.x}},${{t.y - IMP_H/2}}`);
    return;
  }}

  if (e.kind === 'calls') {{
    /* bezier arc between function nodes */
    const dy = t.y - s.y;
    const dx = t.x - s.x;
    const cp1x = s.x + dx * 0.25;
    const cp1y = s.y + (dy > 0 ? 40 : -40);
    const cp2x = t.x - dx * 0.25;
    const cp2y = t.y - (dy > 0 ? 40 : -40);
    edgeG.append('path')
      .attr('class','e-calls')
      .attr('d', `M${{s.x}},${{s.y}} C${{cp1x}},${{cp1y}} ${{cp2x}},${{cp2y}} ${{t.x}},${{t.y}}`);
  }}
}});

/* ═══════════════════════════════════════════════
   NODES
═══════════════════════════════════════════════ */
/* helper: rounded rect + label */
function makeNode(parent, node, w, h, cls) {{
  const grp = parent.append('g')
    .attr('class', cls)
    .attr('transform', `translate(${{node.x - w/2}},${{node.y - h/2}})`);
  grp.append('rect').attr('width', w).attr('height', h).attr('rx', 5);
  return grp;
}}

/* file nodes */
const fileG = g.append('g');
fileNodes.forEach(n => {{
  const grp = makeNode(fileG, n, FILE_W, FILE_H, 'n-file');
  grp.append('text')
    .attr('x', FILE_W/2).attr('y', FILE_H/2 + 1)
    .attr('text-anchor','middle').attr('dominant-baseline','middle')
    .text(n.label.length > 22 ? n.label.slice(0,20)+'…' : n.label);
  grp.append('title').text(n.file);
}});

/* symbol nodes (function / class) */
let selected = null;
const symG = g.append('g');
symNodes.forEach(n => {{
  const grp = makeNode(symG, n, NODE_W, NODE_H, `n-${{n.kind}}`);
  const icon = n.kind === 'function' ? 'ƒ' : '◆';
  const lbl = n.label.length > 17 ? n.label.slice(0,15)+'…' : n.label;
  grp.append('text')
    .attr('x', 8).attr('y', NODE_H/2 - 3)
    .attr('dominant-baseline','middle')
    .text(`${{icon}} ${{lbl}}`);
  if (n.line) {{
    grp.append('text')
      .attr('x', NODE_W - 6).attr('y', NODE_H - 7)
      .attr('text-anchor','end')
      .style('font-size','9px').style('fill','#334155')
      .text(`:${{n.line}}`);
  }}
  grp.append('title').text(`${{n.kind}}: ${{n.label}}\\n${{n.file}}:${{n.line}}`);

  grp.on('click', function() {{
    if (selected) d3.select(selected).classed('sel', false);
    selected = this;
    d3.select(this).classed('sel', true);
    showCode(n);
  }});
}});

/* import nodes */
const impG = g.append('g');
impNodes.forEach(n => {{
  const grp = makeNode(impG, n, IMP_W, IMP_H, 'n-import');
  const lbl = n.label.length > 14 ? n.label.slice(0,12)+'…' : n.label;
  grp.append('text')
    .attr('x', IMP_W/2).attr('y', IMP_H/2 + 1)
    .attr('text-anchor','middle').attr('dominant-baseline','middle')
    .text(lbl);
  grp.append('title').text(n.label);
}});

/* ═══════════════════════════════════════════════
   STATS
═══════════════════════════════════════════════ */
const nF = symNodes.filter(n=>n.kind==='function').length;
const nC = symNodes.filter(n=>n.kind==='class').length;
document.getElementById('stats').textContent =
  `${{fileNodes.length}} 파일  ${{nF}} 함수  ${{nC}} 클래스  ${{impNodes.length}} import  |  ${{GRAPH.edges.length}} 엣지`;

/* ═══════════════════════════════════════════════
   CODE VIEWER
═══════════════════════════════════════════════ */
function esc(s) {{
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}

function showCode(node) {{
  const cp = document.getElementById('cp');
  cp.classList.remove('hidden');

  const fname = node.file.split('/').pop();
  document.getElementById('ch-name').textContent =
    (node.kind === 'function' ? 'ƒ ' : '◆ ') + node.label;
  document.getElementById('ch-meta').textContent =
    `${{fname}}:${{node.line}}  ·  ${{node.language}}`;

  const cb = document.getElementById('cb');
  if (!node.source_code) {{
    cb.innerHTML = '<div class="placeholder">소스코드가 추출되지 않았습니다<br><small style="color:#374151">' + esc(node.file) + '</small></div>';
    return;
  }}
  const lang = node.language === 'typescript' ? 'typescript'
             : node.language === 'javascript' ? 'javascript'
             : node.language === 'java' ? 'java'
             : node.language === 'c' || node.language === 'cpp' ? 'cpp'
             : 'python';
  let highlighted;
  try {{
    highlighted = hljs.highlight(node.source_code, {{language: lang}}).value;
  }} catch(e) {{
    highlighted = esc(node.source_code);
  }}
  cb.innerHTML = `<pre><code class="hljs language-${{lang}}">${{highlighted}}</code></pre>`;
  cb.scrollTop = 0;
}}

function closePanel() {{
  document.getElementById('cp').classList.add('hidden');
  if (selected) {{ d3.select(selected).classed('sel', false); selected = null; }}
}}
</script>
</body>
</html>
"""


class HtmlPreviewExporter:
    def export(self, g: DependencyGraph, out_path: Path, title: str = "NoteBook_MOD") -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        graph_data = {
            "nodes": [dataclasses.asdict(n) for n in g.nodes],
            "edges": [dataclasses.asdict(e) for e in g.edges],
        }
        html = _TEMPLATE.format(
            title=title,
            graph_json=json.dumps(graph_data, ensure_ascii=False),
        )
        out_path.write_text(html, encoding="utf-8")
