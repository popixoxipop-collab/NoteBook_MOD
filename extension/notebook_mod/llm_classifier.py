"""
NoteBook_MOD LLM Classifier
OpenAI API로 Python 함수를 모듈 파일 경로에 분류.

규칙
- gpt-4o-mini (비용 절감) 사용
- State DB의 확정 매핑 / 수정 이력을 few-shot으로 주입
- 응답 파싱 실패 또는 SDK 미설치 시 빈 dict 반환 → caller가 fallback
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


# ── API 키 탐색 ─────────────────────────────────────────
def _parse_key_file(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError, UnicodeDecodeError):
        return None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^\s*OPENAI_API_KEY\s*=\s*['\"]?([^'\"]+)['\"]?\s*$", line)
        if m:
            return m.group(1).strip()
        # 단순히 키만 한 줄로 적힌 경우
        if line.startswith("sk-") and "=" not in line:
            return line
    return None


def get_openai_key() -> str | None:
    """우선순위: 환경변수 → ./api_key.txt → ~/api_key.txt"""
    env = os.environ.get("OPENAI_API_KEY")
    if env and env.strip():
        return env.strip()

    cwd_key = Path(os.getcwd()) / "api_key.txt"
    if cwd_key.exists():
        k = _parse_key_file(cwd_key)
        if k:
            return k

    home_key = Path.home() / "api_key.txt"
    if home_key.exists():
        k = _parse_key_file(home_key)
        if k:
            return k

    return None


# ── 프롬프트 빌더 ───────────────────────────────────────
_SYSTEM_PROMPT = (
    "당신은 Python 함수를 적절한 모듈 파일 경로로 분류하는 전문가입니다. "
    "프로젝트 컨벤션과 사용자 수정 이력을 반드시 존중하세요. "
    "출력은 반드시 유효한 JSON 객체 하나만 반환합니다 (markdown 코드펜스 금지)."
)


def _format_categories(categories: list[dict[str, str]]) -> str:
    lines = ["[카테고리]"]
    for c in categories:
        name = c.get("name", "")
        desc = c.get("description", "")
        lines.append(f"- {name}/: {desc}".rstrip())
    return "\n".join(lines)


def _format_confirmed(confirmed_mappings: dict[str, dict[str, Any]]) -> str:
    if not confirmed_mappings:
        return "[이 프로젝트 확정 사례]\n(없음)"
    lines = ["[이 프로젝트 확정 사례]"]
    # 최대 20개만 (토큰 절약)
    for name, info in list(confirmed_mappings.items())[:20]:
        path = info.get("path", "")
        src  = info.get("source", "")
        lines.append(f"{name} → {path} ({src})")
    return "\n".join(lines)


def _format_corrections(corrections: list[dict[str, Any]]) -> str:
    if not corrections:
        return "[수정 이력]\n(없음)"
    lines = ["[수정 이력]"]
    for c in corrections[:10]:
        lines.append(
            f"{c.get('funcName')}: {c.get('fromPath')} → {c.get('toPath')} (사용자 수정)"
        )
    return "\n".join(lines)


def _format_targets(functions: list[dict[str, Any]]) -> str:
    lines = ["[분류 대상]"]
    for f in functions:
        name = f.get("funcName", "")
        src  = (f.get("sourceCode") or "").strip()
        # 너무 긴 함수는 자르기 (토큰 절약)
        if len(src) > 1200:
            src = src[:1200] + "\n# ... (truncated)"
        lines.append(f"\n함수명: {name}\n코드:\n{src}")
    return "\n".join(lines)


def _build_user_prompt(
    functions: list[dict[str, Any]],
    categories: list[dict[str, str]],
    confirmed_mappings: dict[str, dict[str, Any]],
    corrections: list[dict[str, Any]],
) -> str:
    instructions = (
        "각 함수에 대해 가장 적절한 파일 경로(`카테고리/파일명.py`)를 정하세요.\n"
        "- 확정 사례와 수정 이력의 패턴을 우선 적용하세요.\n"
        "- 비슷한 책임의 함수는 같은 파일로 묶으세요.\n"
        "- confidence는 0.0~1.0 실수.\n\n"
        "응답 형식 (JSON only):\n"
        '{\n'
        '  "<funcName>": {"path": "<dir>/<file>.py", "confidence": 0.0-1.0, "reason": "<짧은 근거>"}\n'
        '}\n'
    )
    return "\n\n".join([
        _format_categories(categories),
        _format_confirmed(confirmed_mappings),
        _format_corrections(corrections),
        _format_targets(functions),
        instructions,
    ])


# ── JSON 파싱 (코드펜스 등 방어) ────────────────────────
def _extract_json(text: str) -> dict[str, Any]:
    if not text:
        return {}
    # ```json ... ``` 펜스 제거
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    # 가장 바깥 중괄호 블록만 추출
    start = text.find("{")
    end   = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    snippet = text[start : end + 1]
    try:
        obj = json.loads(snippet)
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        return {}


# ── 메인 분류 함수 ──────────────────────────────────────
def classify_functions(
    functions: list[dict[str, Any]],
    categories: list[dict[str, str]],
    confirmed_mappings: dict[str, dict[str, Any]],
    corrections: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """
    OpenAI LLM으로 함수를 분류.
    실패 시 빈 dict 반환 (caller가 fallback 처리).

    반환 형식:
      { funcName: {"path": str, "confidence": float, "reason": str} }
    """
    if not functions:
        return {}

    api_key = get_openai_key()
    if not api_key:
        return {}

    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        return {}

    user_prompt = _build_user_prompt(
        functions, categories, confirmed_mappings, corrections
    )

    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=1500,
            response_format={"type": "json_object"},
            timeout=30,
        )
        content = resp.choices[0].message.content or ""
    except Exception:
        return {}

    raw = _extract_json(content)
    if not raw:
        return {}

    # 정규화: path/confidence/reason 키만 통과
    result: dict[str, dict[str, Any]] = {}
    for name, info in raw.items():
        if not isinstance(info, dict):
            continue
        path = info.get("path") or info.get("file_path")
        if not isinstance(path, str) or not path.strip():
            continue
        try:
            conf = float(info.get("confidence", 0.7))
        except (TypeError, ValueError):
            conf = 0.7
        conf = max(0.0, min(1.0, conf))
        reason = info.get("reason", "") if isinstance(info.get("reason", ""), str) else ""
        result[name] = {
            "path":       path.strip(),
            "confidence": conf,
            "reason":     reason,
        }
    return result
