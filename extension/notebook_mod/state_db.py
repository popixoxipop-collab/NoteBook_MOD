"""
NoteBook_MOD State Database
SQLite 기반 영속 상태 저장소.

- confirmed_mappings: funcName → filePath 확정 매핑 (LLM/human 출처)
- corrections: 사용자 수정 이력 (few-shot 재료)
- categories: 디렉토리 카테고리 정의
"""
from __future__ import annotations

import os
import sqlite3
from typing import Any


_DEFAULT_CATEGORIES: list[tuple[str, str]] = [
    ("agents",     "LLM 호출 / 에이전트 노드 함수"),
    ("db",         "데이터베이스 읽기/쓰기 작업"),
    ("graph",      "LangGraph build/route/compile 함수"),
    ("utils",      "유틸리티 / 로딩 / 설정 함수"),
    ("models",     "데이터 모델 / 클래스"),
    ("evaluation", "성능 지표 / 점수 계산 (BLEU, ROUGE 등)"),
    ("prompts",    "프롬프트 템플릿 / 시스템 메시지"),
]


class StateDB:
    """SQLite 기반 NoteBook_MOD State 저장소."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        parent = os.path.dirname(db_path)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        self._ensure_schema()
        self._seed_categories()

    # ── 내부 헬퍼 ────────────────────────────────────────
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS confirmed_mappings (
                  func_name    TEXT PRIMARY KEY,
                  file_path    TEXT NOT NULL,
                  source       TEXT NOT NULL,
                  confidence   REAL DEFAULT 1.0,
                  confirmed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS corrections (
                  id           INTEGER PRIMARY KEY AUTOINCREMENT,
                  func_name    TEXT NOT NULL,
                  from_path    TEXT NOT NULL,
                  to_path      TEXT NOT NULL,
                  corrected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS categories (
                  name        TEXT PRIMARY KEY,
                  description TEXT DEFAULT ''
                );
                """
            )

    def _seed_categories(self) -> None:
        """카테고리 테이블이 비어 있으면 기본값 삽입."""
        with self._connect() as conn:
            cur = conn.execute("SELECT COUNT(*) AS n FROM categories;")
            n = cur.fetchone()["n"]
            if n == 0:
                conn.executemany(
                    "INSERT INTO categories(name, description) VALUES (?, ?);",
                    _DEFAULT_CATEGORIES,
                )

    # ── confirmed_mappings ──────────────────────────────
    def get_mapping(self, func_name: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT file_path FROM confirmed_mappings WHERE func_name = ?;",
                (func_name,),
            ).fetchone()
            return row["file_path"] if row else None

    def set_mapping(
        self,
        func_name: str,
        file_path: str,
        source: str,
        confidence: float = 1.0,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO confirmed_mappings(func_name, file_path, source, confidence)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(func_name) DO UPDATE SET
                    file_path    = excluded.file_path,
                    source       = excluded.source,
                    confidence   = excluded.confidence,
                    confirmed_at = CURRENT_TIMESTAMP;
                """,
                (func_name, file_path, source, float(confidence)),
            )

    def get_all_mappings(self) -> dict[str, dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT func_name, file_path, source, confidence FROM confirmed_mappings;"
            ).fetchall()
            return {
                r["func_name"]: {
                    "path":       r["file_path"],
                    "source":     r["source"],
                    "confidence": r["confidence"],
                }
                for r in rows
            }

    # ── corrections ─────────────────────────────────────
    def add_correction(self, func_name: str, from_path: str, to_path: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO corrections(func_name, from_path, to_path)
                VALUES (?, ?, ?);
                """,
                (func_name, from_path, to_path),
            )

    def get_corrections(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT func_name, from_path, to_path, corrected_at
                FROM corrections
                ORDER BY corrected_at DESC
                LIMIT 50;
                """
            ).fetchall()
            return [
                {
                    "funcName":    r["func_name"],
                    "fromPath":    r["from_path"],
                    "toPath":      r["to_path"],
                    "correctedAt": r["corrected_at"],
                }
                for r in rows
            ]

    # ── categories ──────────────────────────────────────
    def get_categories(self) -> list[dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, description FROM categories ORDER BY name;"
            ).fetchall()
            return [
                {"name": r["name"], "description": r["description"] or ""}
                for r in rows
            ]

    def set_category(self, name: str, description: str = "") -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO categories(name, description)
                VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET description = excluded.description;
                """,
                (name, description or ""),
            )

    def delete_category(self, name: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM categories WHERE name = ?;", (name,))
