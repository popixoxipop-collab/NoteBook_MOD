"""
POST /notebook-mod/analyze
함수 소스코드들을 받아 임베딩 → 코사인 유사도 → 클러스터링 → {funcName: filePath} 반환.
sentence-transformers 없으면 TF-IDF로 자동 폴백.
"""
import json
import re
import numpy as np
from jupyter_server.base.handlers import APIHandler
from tornado.web import authenticated

# ── 모델 캐시 ───────────────────────────────────────────
_embed_model      = None
_embed_model_type = None


def _get_embeddings(texts: list[str]) -> np.ndarray:
    global _embed_model, _embed_model_type

    try:
        from sentence_transformers import SentenceTransformer
        if _embed_model_type != 'st':
            _embed_model      = SentenceTransformer('all-MiniLM-L6-v2')
            _embed_model_type = 'st'
        return _embed_model.encode(texts, show_progress_bar=False)

    except ImportError:
        from sklearn.feature_extraction.text import TfidfVectorizer
        if _embed_model_type != 'tfidf':
            _embed_model      = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5))
            _embed_model_type = 'tfidf'
        mat = _embed_model.fit_transform(texts).toarray()
        return mat.astype(np.float32)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb)) if na and nb else 0.0


def _cluster(embeddings: list[np.ndarray], threshold: float) -> list[list[int]]:
    """
    Greedy 클러스터링:
    새 함수가 기존 클러스터의 모든 멤버와 similarity >= threshold 이면 합류,
    아니면 새 클러스터 생성.
    """
    clusters: list[list[int]] = []
    for i, emb in enumerate(embeddings):
        placed = False
        for cluster in clusters:
            if all(_cosine(emb, embeddings[j]) >= threshold for j in cluster):
                cluster.append(i)
                placed = True
                break
        if not placed:
            clusters.append([i])
    return clusters


# ── 규칙 기반 디렉토리 추론 (Python 사이드) ─────────────
def _infer_dir(func_name: str) -> str:
    lower = func_name.lower().lstrip('_')
    if re.search(r'_node$|_agent$', lower):                  return 'agents'
    if re.match(r'(build|route|compile|create_graph)_', lower): return 'graph'
    if re.match(r'(init_db|save_|get_.*db|fetch_.*db)', lower):  return 'db'
    if re.match(r'(load|get|read|fetch|setup|configure)_', lower): return 'utils'
    return ''


def _cluster_filename(names: list[str]) -> str:
    """클러스터 대표 파일명 — 공통 패턴 우선, 없으면 가장 짧은 이름"""
    stripped = [n.lstrip('_') for n in names]
    if len(stripped) == 1:
        return stripped[0]
    if all(re.search(r'node|agent', s) for s in stripped):   return 'nodes'
    if all(re.match(r'(load|get|read|fetch|setup)', s) for s in stripped): return 'helpers'
    if all(re.search(r'db|database|record', s) for s in stripped): return 'database'
    return min(stripped, key=len)


class AnalyzeHandler(APIHandler):

    @authenticated
    async def get(self):
        """임베딩 모델 상태 반환"""
        try:
            import sentence_transformers  # noqa: F401
            self.finish(json.dumps({'status': 'ok', 'backend': 'sentence-transformers'}))
        except ImportError:
            self.finish(json.dumps({'status': 'ok', 'backend': 'tfidf-fallback'}))

    @authenticated
    async def post(self):
        body      = json.loads(self.request.body)
        functions = body.get('functions', [])    # [{funcName, sourceCode, isClass}]
        threshold = float(body.get('threshold', 0.65))

        if not functions:
            self.finish(json.dumps({}))
            return

        names    = [f['funcName']   for f in functions]
        sources  = [f['sourceCode'] for f in functions]
        is_class = [f.get('isClass', False) for f in functions]

        # 1. 클래스는 이름 규칙으로 즉시 경로 결정 (임베딩 스킵)
        result: dict[str, str] = {}
        embed_indices: list[int] = []
        for i, (name, cls) in enumerate(zip(names, is_class)):
            if cls:
                low = name.lower()
                if low.endswith('state'):    result[name] = 'state.py'
                elif low.endswith('config'): result[name] = 'config.py'
                elif low.endswith('schema'): result[name] = 'schema.py'
                else:                        result[name] = f'models/{name.lstrip("_")}.py'
            else:
                embed_indices.append(i)

        if not embed_indices:
            self.finish(json.dumps(result))
            return

        embed_names   = [names[i]   for i in embed_indices]
        embed_sources = [sources[i] for i in embed_indices]

        # 2. 임베딩 (함수만)
        embeddings = _get_embeddings(embed_sources)

        # 3. 디렉토리별 그룹 분리 (규칙 기반)
        dir_groups: dict[str, list[int]] = {}
        for j, name in enumerate(embed_names):
            d = _infer_dir(name)
            dir_groups.setdefault(d, []).append(j)

        # 4. 디렉토리 내부에서 유사도 기반 클러스터링
        for d, indices in dir_groups.items():
            sub_embs     = [embeddings[i] for i in indices]
            sub_names    = [embed_names[i] for i in indices]
            clusters     = _cluster(sub_embs, threshold)

            for cluster in clusters:
                cluster_names = [sub_names[ci] for ci in cluster]
                file_stem     = _cluster_filename(cluster_names)
                path          = f'{d}/{file_stem}.py' if d else f'{file_stem}.py'
                for name in cluster_names:
                    result[name] = path

        self.finish(json.dumps(result))
