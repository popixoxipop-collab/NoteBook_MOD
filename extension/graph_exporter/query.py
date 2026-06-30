"""Keyword search over graph.json — token-efficient LLM lookup.

D5: keyword-based graph query
  WHY: graph.json 전체 읽기 = 50K+ 토큰; 쿼리 결과만 = ~1-2K 토큰.
       graphify와 동일한 "관련 노드만 반환" 패턴을 graph.json 위에 구현.
  COST: 임베딩 없음 → 동의어/오타 미스; 단순 substring+term 매칭만.
  EXIT: _score()를 sentence-transformers cosine sim으로 교체하면 의미 검색 가능.
"""
import json
import re
from pathlib import Path


def _terms(text: str) -> set[str]:
    """소문자 단어 집합. 1-2글자 단어 제거."""
    return {t for t in re.split(r"[\W_]+", text.lower()) if len(t) >= 3}


def _score(node: dict, query_terms: set[str]) -> float:
    label_hits = len(query_terms & _terms(node.get("label", "")))
    file_hits  = len(query_terms & _terms(Path(node.get("file", "")).stem))
    kind_hit   = 1.0 if node.get("kind", "") in query_terms else 0.0
    return label_hits * 3.0 + file_hits * 1.5 + kind_hit * 1.0


def search(graph_json: Path, query: str, top_k: int = 20) -> str:
    """Return compact text representation of the top-k relevant nodes + their edges."""
    data = json.loads(graph_json.read_text())
    nodes: list[dict] = data["nodes"]
    edges: list[dict] = data["edges"]

    q_terms = _terms(query)

    # 1. Score all nodes
    scored = sorted(
        [(n, _score(n, q_terms)) for n in nodes],
        key=lambda x: -x[1],
    )
    top_nodes = [n for n, s in scored if s > 0][:top_k]
    top_ids   = {n["id"] for n in top_nodes}

    # 2. Collect edges that touch top nodes; gather 1-hop neighbors
    neighbor_ids: set[str] = set()
    hit_edges: list[dict] = []
    for e in edges:
        src_in = e["source"] in top_ids
        tgt_in = e["target"] in top_ids
        if src_in or tgt_in:
            hit_edges.append(e)
            if src_in:
                neighbor_ids.add(e["target"])
            if tgt_in:
                neighbor_ids.add(e["source"])

    # 3. Add neighbors (cap at top_k // 2, avoid duplicates)
    extra = [n for n in nodes if n["id"] in (neighbor_ids - top_ids)][: top_k // 2]
    all_nodes = top_nodes + extra
    all_ids   = {n["id"] for n in all_nodes}

    # 4. Filter edges to only those fully within all_nodes
    final_edges = [e for e in hit_edges if e["source"] in all_ids and e["target"] in all_ids]

    # 5. Build label lookup for compact edge display
    id_to_label = {n["id"]: n["label"] for n in all_nodes}

    # ── Format output ──────────────────────────────────────────────
    lines: list[str] = []
    lines.append(f'[query: "{query}"] → {len(all_nodes)} nodes, {len(final_edges)} edges')
    lines.append(f'(full graph: {len(nodes)} nodes, {len(edges)} edges)\n')

    lines.append("NODES:")
    for n in all_nodes:
        ver      = f' [{n["version"]}]' if n.get("version") else ""
        line_no  = f':{n["line"]}' if n.get("line") else ""
        file_short = Path(n.get("file", "")).name
        lines.append(f'  {n["kind"]:<12} {n["label"]:<32} {file_short}{line_no}{ver}')

    if final_edges:
        lines.append("\nEDGES:")
        by_kind: dict[str, list[dict]] = {}
        for e in final_edges:
            by_kind.setdefault(e["kind"], []).append(e)
        for kind in ("contains", "imports", "calls", "uses"):
            for e in by_kind.get(kind, [])[:30]:
                src = id_to_label.get(e["source"], e["source"].split("::")[-1])
                tgt = id_to_label.get(e["target"], e["target"].split("::")[-1])
                lines.append(f'  {src} → {tgt}  [{kind}]')

    return "\n".join(lines)
