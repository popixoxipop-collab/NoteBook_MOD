"""
NoteBook_MOD 백엔드 핸들러.

신규 3단계 분류 파이프라인:
  1) StateDB 확정 매핑 hit → 즉시 반환 (LLM 호출 없음)
  2) miss → OpenAI LLM 분류 (State few-shot 주입)
  3) LLM 실패/부재 → 규칙 기반 fallback (sentence-transformers/TF-IDF + 클러스터링)

핸들러:
  - AnalyzeHandler   : GET 상태 / POST 메인 분류
  - StateHandler     : GET State 전체 / POST 확정/수정
  - CategoryHandler  : GET 카테고리 / POST add|delete
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import numpy as np
from jupyter_server.base.handlers import APIHandler
from tornado.web import authenticated

from .state_db import StateDB
from .llm_classifier import classify_functions, get_openai_key


# ── 모델 캐시 ───────────────────────────────────────────
_embed_model      = None
_embed_model_type = None


def _state_db() -> StateDB:
    """요청 시점의 cwd 기준 StateDB."""
    return StateDB(os.path.join(os.getcwd(), ".nbmod_state.db"))


# ──────────────────────────────────────────────────────
# 규칙 기반 fallback (기존 코드 보존)
# ──────────────────────────────────────────────────────
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
    """Greedy 클러스터링 — 새 함수가 기존 클러스터 멤버 모두와 sim ≥ threshold면 합류."""
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


def _infer_dir(func_name: str) -> str:
    lower = func_name.lower().lstrip('_')
    if re.search(r'_node$|_agent$', lower):                       return 'agents'
    if re.match(r'(build|route|compile|create_graph)_', lower):   return 'graph'
    if re.match(r'(init_db|save_|get_.*db|fetch_.*db)', lower):   return 'db'
    if re.match(r'(load|get|read|fetch|setup|configure)_', lower): return 'utils'
    return ''


def _cluster_filename(names: list[str]) -> str:
    stripped = [n.lstrip('_') for n in names]
    if len(stripped) == 1:
        return stripped[0]
    if all(re.search(r'node|agent', s) for s in stripped):                  return 'nodes'
    if all(re.match(r'(load|get|read|fetch|setup)', s) for s in stripped):  return 'helpers'
    if all(re.search(r'db|database|record', s) for s in stripped):          return 'database'
    return min(stripped, key=len)


def _rule_based_classify(
    embed_names: list[str],
    embed_sources: list[str],
    threshold: float,
) -> dict[str, str]:
    """
    기존 규칙 기반 분류 (sentence-transformers/TF-IDF + 클러스터링).
    반환: { funcName: filePath }
    """
    embeddings = _get_embeddings(embed_sources)

    dir_groups: dict[str, list[int]] = {}
    for j, name in enumerate(embed_names):
        d = _infer_dir(name)
        dir_groups.setdefault(d, []).append(j)

    out: dict[str, str] = {}
    for d, indices in dir_groups.items():
        sub_embs  = [embeddings[i] for i in indices]
        sub_names = [embed_names[i] for i in indices]
        clusters  = _cluster(sub_embs, threshold)

        for cluster in clusters:
            cluster_names = [sub_names[ci] for ci in cluster]
            file_stem     = _cluster_filename(cluster_names)
            path          = f'{d}/{file_stem}.py' if d else f'{file_stem}.py'
            for name in cluster_names:
                out[name] = path
    return out


def _classify_class(name: str) -> str:
    low = name.lower()
    if low.endswith('state'):   return 'state.py'
    if low.endswith('config'):  return 'config.py'
    if low.endswith('schema'):  return 'schema.py'
    return f'models/{name.lstrip("_")}.py'


# ──────────────────────────────────────────────────────
# AnalyzeHandler
# ──────────────────────────────────────────────────────
class AnalyzeHandler(APIHandler):

    @authenticated
    async def get(self):
        """백엔드 상태 반환: openai > sentence-transformers > tfidf-fallback."""
        backend = "tfidf-fallback"
        if get_openai_key():
            try:
                import openai  # noqa: F401
                backend = "openai"
            except ImportError:
                pass
        if backend == "tfidf-fallback":
            try:
                import sentence_transformers  # noqa: F401
                backend = "sentence-transformers"
            except ImportError:
                pass
        self.finish(json.dumps({"status": "ok", "backend": backend}))

    @authenticated
    async def post(self):
        body      = json.loads(self.request.body)
        functions = body.get('functions', [])    # [{funcName, sourceCode, isClass}]
        threshold = float(body.get('threshold', 0.65))

        if not functions:
            self.finish(json.dumps({}))
            return

        db = _state_db()

        result: dict[str, dict[str, Any]] = {}
        llm_queue: list[dict[str, Any]]   = []
        class_pending: list[str]          = []

        # ── 1단계: StateDB 조회 ─────────────────────────
        for f in functions:
            name     = f.get('funcName')
            if not name:
                continue
            is_class = bool(f.get('isClass', False))

            cached = db.get_mapping(name)
            if cached:
                result[name] = {"path": cached, "source": "state", "confidence": 1.0}
                continue

            if is_class:
                class_pending.append(name)
            else:
                llm_queue.append({
                    "funcName":   name,
                    "sourceCode": f.get('sourceCode', ''),
                    "isClass":    False,
                })

        # ── 2단계: LLM 분류 (miss만) ────────────────────
        llm_result: dict[str, dict[str, Any]] = {}
        if llm_queue:
            categories         = db.get_categories()
            confirmed_mappings = db.get_all_mappings()
            corrections        = db.get_corrections()
            try:
                llm_result = classify_functions(
                    functions=llm_queue,
                    categories=categories,
                    confirmed_mappings=confirmed_mappings,
                    corrections=corrections,
                )
            except Exception:
                llm_result = {}

        # LLM 결과 → result + StateDB 저장
        llm_handled: set[str] = set()
        for name, info in llm_result.items():
            path = info.get("path")
            conf = float(info.get("confidence", 0.7))
            if not path:
                continue
            result[name] = {"path": path, "source": "llm", "confidence": conf}
            try:
                db.set_mapping(name, path, source="llm", confidence=conf)
            except Exception:
                pass
            llm_handled.add(name)

        # ── 3단계: LLM 미처리 함수 → 규칙 기반 fallback ─
        fallback_queue = [f for f in llm_queue if f["funcName"] not in llm_handled]
        if fallback_queue:
            embed_names   = [f["funcName"]   for f in fallback_queue]
            embed_sources = [f["sourceCode"] for f in fallback_queue]
            try:
                fb_map = _rule_based_classify(embed_names, embed_sources, threshold)
            except Exception:
                fb_map = {n: f"{n}.py" for n in embed_names}

            for name, path in fb_map.items():
                result[name] = {"path": path, "source": "fallback", "confidence": 0.4}

        # ── 클래스 처리 (State miss인 경우만) ───────────
        for name in class_pending:
            path = _classify_class(name)
            result[name] = {"path": path, "source": "rule-class", "confidence": 0.6}

        self.finish(json.dumps(result))


# ──────────────────────────────────────────────────────
# StateHandler
# ──────────────────────────────────────────────────────
class StateHandler(APIHandler):

    @authenticated
    async def get(self):
        db = _state_db()
        payload = {
            "mappings":    db.get_all_mappings(),
            "categories":  db.get_categories(),
            "corrections": db.get_corrections(),
        }
        self.finish(json.dumps(payload))

    @authenticated
    async def post(self):
        body      = json.loads(self.request.body)
        func_name = body.get("funcName")
        path      = body.get("path")
        action    = body.get("action", "confirm")
        from_path = body.get("fromPath")

        if not func_name or not path:
            self.set_status(400)
            self.finish(json.dumps({"error": "funcName and path are required"}))
            return

        db = _state_db()

        if action == "correct":
            from_path = from_path or (db.get_mapping(func_name) or "")
            db.add_correction(func_name, from_path or "", path)
            db.set_mapping(func_name, path, source="human", confidence=1.0)
        elif action == "confirm":
            db.set_mapping(func_name, path, source="human", confidence=1.0)
        else:
            self.set_status(400)
            self.finish(json.dumps({"error": f"unknown action: {action}"}))
            return

        self.finish(json.dumps({
            "status":   "ok",
            "funcName": func_name,
            "path":     path,
            "action":   action,
        }))


# ──────────────────────────────────────────────────────
# CategoryHandler
# ──────────────────────────────────────────────────────
class CategoryHandler(APIHandler):

    @authenticated
    async def get(self):
        db = _state_db()
        self.finish(json.dumps({"categories": db.get_categories()}))

    @authenticated
    async def post(self):
        body        = json.loads(self.request.body)
        action      = body.get("action")
        name        = body.get("name")
        description = body.get("description", "")

        if not action or not name:
            self.set_status(400)
            self.finish(json.dumps({"error": "action and name are required"}))
            return

        db = _state_db()

        if action == "add":
            db.set_category(name, description)
        elif action == "delete":
            db.delete_category(name)
        else:
            self.set_status(400)
            self.finish(json.dumps({"error": f"unknown action: {action}"}))
            return

        self.finish(json.dumps({
            "status":     "ok",
            "action":     action,
            "categories": db.get_categories(),
        }))
