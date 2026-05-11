# NoteBook_MOD — MVP 설계문서

> 노트북 자동 모듈화 SaaS  
> 작성일: 2026-05-11  
> 상태: DRAFT

---

## 1. 문제 정의

### 현상

Jupyter Notebook은 탐색·프로토타이핑 도구로 설계됐지만, 실제로는 프로덕션 직전까지 사용된다.
결과적으로 한 파일 안에 모든 것이 뒤섞인다.

```
# 현실의 노트북 (실제 레퍼런스: Step1_상품리뷰분석_Agent_1_완성.ipynb, 62 cells)
ReviewState (데이터 구조)
analyzer_node (분석 로직)
critic_node (검증 로직)
supervisor_node (흐름 제어)
DB 연결/생성/저장 코드
Streamlit UI 코드
실행 테스트 코드
→ 전부 한 파일, 중복 포함
```

### 위반되는 설계 원칙

| 원칙 | 위반 내용 |
|---|---|
| 단일 책임(SRP) | 분석·검증·DB·UI가 한 파일에 혼재 |
| 관심사 분리(SoC) | Agent 로직과 Streamlit UI가 같은 셀에 |
| 재사용성 | app.py에 Agent 코드 통째로 복붙 (중복) |
| 테스트 가능성 | 함수를 개별 import해서 테스트 불가 |

### 기존 해결책의 한계

| 도구 | 형태 | 한계 |
|---|---|---|
| **nbconvert** | CLI | 한 덩어리 .py로 단순 변환, 구조 분리 없음 |
| **nbrefactor** | CLI 라이브러리 | 개발자 직접 실행, 웹 서비스 없음 |
| **Soorgeon** (Ploomber) | 오픈소스 CLI | 파이프라인 변환 특화, 모듈화 아님 |
| **MASA** (arXiv:2511.07257) | 논문 | 연구 수준, 상용 서비스 없음 |
| **CodeAlchemist** | 논문 | API 변환 특화, 서비스 없음 |
| **jupytext** | CLI | 노트북↔py 동기화, 구조 분리 없음 |

**결론: "노트북 업로드 → 자동 모듈화 → 패키지 구조 export" 웹 서비스는 현재 전무.**

---

## 2. 솔루션 개요

### 핵심 가치

> 노트북을 업로드하면, LLM이 셀을 분석해 함수/클래스/레이어별로 자동 분리하고  
> import 연결이 완성된 Python 패키지 구조로 내려받을 수 있다.

### Before / After

```
[Before] 노트북 1개 (62 cells, 모든 코드 혼재)

[After]
myproject/
├── __init__.py
├── state.py            ← ReviewState
├── agents/
│   ├── __init__.py
│   ├── analyzer_node.py
│   ├── critic_node.py
│   └── supervisor_node.py
├── graph/
│   ├── __init__.py
│   ├── route_next.py
│   └── builder.py
├── db/
│   ├── __init__.py
│   ├── init_db.py
│   └── save_result.py
├── ui/
│   └── app.py
└── tests/
    ├── test_analyzer.py  ← 자동 생성
    └── test_critic.py
```

---

## 3. 시장 분석

### 타깃 사용자

| 세그먼트 | 페인포인트 |
|---|---|
| **데이터 사이언티스트** | 실험 노트북 → 프로덕션 전환 시 매번 수동 정리 |
| **AI 개발자 (LLM/Agent)** | Agent 노드가 노트북에 뒤섞임, 재사용 불가 |
| **부트캠프 수료생** | 포트폴리오 노트북을 패키지로 만들고 싶음 |
| **팀 단위 ML 프로젝트** | 노트북 공유 시 의존성 파악 불가 |

### 시장 규모 (간이 추정)

- Jupyter 사용자: 전 세계 약 1,000만 명 이상
- GitHub 공개 노트북: 700만 개 이상
- 데이터 사이언티스트 중 "노트북 → 프로덕션" 전환 경험: 대부분

---

## 4. MVP 기능 범위

### In Scope (v0.1)

| # | 기능 | 설명 |
|---|---|---|
| F1 | **노트북 업로드** | .ipynb 파일 드래그앤드롭 |
| F2 | **셀 분석 & 분류** | LLM이 각 셀을 레이어로 분류 (state/agent/db/ui/test/util) |
| F3 | **의존성 그래프 시각화** | 함수 간 호출 관계 그래프 표시 |
| F4 | **모듈 구조 미리보기** | 분리될 파일 구조 트리 미리보기 |
| F5 | **패키지 다운로드** | 분리된 .py 파일들 + __init__.py ZIP으로 다운로드 |
| F6 | **import 자동 연결** | 분리된 파일 간 import 문 자동 생성 |

### Out of Scope (v0.1)

- GitHub 직접 push (v0.2)
- 팀 협업 / 버전 관리 (v0.3)
- 자동 테스트 생성 (v0.2)
- CI/CD 연동 (v1.0)

---

## 5. 핵심 알고리즘

### Step 1 — 셀 파싱

```python
# .ipynb → 코드 셀만 추출
cells = [cell for cell in nb['cells'] if cell['cell_type'] == 'code']
```

### Step 2 — LLM 셀 분류 (MASA 논문 참조)

MASA(arXiv:2511.07257)의 멀티에이전트 접근법을 참조.
각 셀을 LLM에 전달해 레이어 태그 부여:

```
레이어 태그:
  STATE   → TypedDict, dataclass, 데이터 구조
  AGENT   → def *_node(), 비즈니스 로직 함수
  GRAPH   → StateGraph, builder, 라우팅
  DB      → sqlite3, 쿼리, CRUD 함수
  UI      → streamlit, gradio, flask
  UTIL    → 공통 유틸, API 키 로드
  TEST    → 실행 테스트, assert
  INSTALL → pip install, !apt-get
  IMPORT  → import 구문
```

### Step 3 — 의존성 분석

```python
import ast

def extract_dependencies(cell_source: str) -> list[str]:
    tree = ast.parse(cell_source)
    calls = [node.func.id for node in ast.walk(tree)
             if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name)]
    return calls
```

- AST 파싱으로 함수 호출 관계 추출
- 태그 + 의존성 → 파일 배치 결정

### Step 4 — 파일 생성 & import 연결

```python
# 예시: agents/analyzer_node.py 생성 시
header = """from state import ReviewState
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json, re
"""
```

- 각 모듈이 참조하는 심볼을 역추적해 import 자동 삽입
- CodeAlchemist의 96% 정확도 Notebook Converter 방식 참조

---

## 6. 핵심 UX — 노트북 인라인 모듈 뷰어 (JupyterLab Extension)

### 개념

모듈화 후 노트북에서 함수 코드가 사라지는 대신,
**압축된 인라인 뱃지**로 대체된다. Python IDE의 hover docstring과 동일한 UX.

### 셀 표현 변화

```
[Before — 모듈화 전]                [After — 모듈화 후]

def analyzer_node(state):     →     def 📄 analyzer_node
    review = state["review"]             ↑ 박스/뱃지로 처리된 함수명
    system_prompt = """...               (본문 30줄 숨김)
    messages = [...]
    response = llm.invoke(...)
    return {"analyzer_result": result}
```

### 인터랙션 상세

| 동작 | 결과 |
|---|---|
| **기본 상태** | `def 📄 analyzer_node` — 파일 아이콘 + 함수명만 표시 |
| **마우스 호버** | 원본 함수 코드 전체가 툴팁/팝오버로 표시 (syntax highlight 포함) |
| **클릭** | 연결된 `analyzer_node.py` 파일이 JupyterLab 우측 패널에서 열림 |
| **더블클릭** | 뱃지가 풀리며 노트북 셀에 코드 인라인 전개 (일반 셀처럼 편집 가능) |

### 시각적 표현

```
┌─ 셀 [5] ─────────────────────────────────────────┐
│                                                   │
│  def ┌─────────────────┐                          │
│      │ 📄 analyzer_node│  ← 클릭/호버 가능한 뱃지 │
│      └─────────────────┘                          │
│                                                   │
│  def ┌──────────────┐                             │
│      │ 📄 critic_node│                            │
│      └──────────────┘                             │
└───────────────────────────────────────────────────┘

             ↓ analyzer_node 호버 시

┌─────────────────────────────────────────────┐
│ 📄 agents/analyzer_node.py                  │
│─────────────────────────────────────────────│
│ def analyzer_node(state: ReviewState):      │
│     review = state["review"]                │
│     system_prompt = """...ABSA 전문가..."""  │
│     messages = [SystemMessage(...), ...]    │
│     response = llm.invoke(messages)         │
│     return {"analyzer_result": result}      │
└─────────────────────────────────────────────┘
```

### 구현 방식 — JupyterLab Extension

```
JupyterLab Extension (TypeScript)
  │
  ├── CodeMirror 커스텀 데코레이터
  │     def/class 키워드 다음 함수명 감지
  │     → 뱃지 렌더링으로 교체
  │
  ├── Hover 핸들러
  │     연결된 .py 파일 읽어서 팝오버 렌더링
  │     (CodeMirror syntax highlight 적용)
  │
  ├── Click 핸들러
  │     JupyterLab 파일 브라우저 API로 해당 .py 파일 오픈
  │     → 우측 split panel에서 열림
  │
  └── 메타데이터 연동
        셀 metadata에 {"modularized": true, "file": "agents/analyzer_node.py"}
        저장 → 노트북 재오픈 시에도 뱃지 유지
```

### 참조 UX

| 레퍼런스 | 유사한 기능 |
|---|---|
| VS Code Peek Definition (Alt+F12) | hover 시 코드 미리보기 |
| Python IDE 내장함수 docstring 툴팁 | str.split 위 마우스 → 시그니처+설명 팝업 |
| JupyterLab Completer | 자동완성 팝오버 UI 패턴 |
| GitHub Code Navigation | 클릭 → 정의로 이동 |

---

## 7. 시스템 아키텍처

```
[사용자 브라우저]
      │ .ipynb 업로드
      ▼
[Frontend — Next.js]
  - 업로드 UI
  - 파일 트리 미리보기
  - 의존성 그래프 (D3.js or React Flow)
  - ZIP 다운로드 버튼
      │
      ▼
[Backend — FastAPI]
  - /upload    : 노트북 수신 & 파싱
  - /analyze   : LLM 셀 분류 (비동기)
  - /preview   : 모듈 구조 JSON 반환
  - /export    : ZIP 생성 & 다운로드
      │
      ├── [LLM — Claude Sonnet / GPT-4o-mini]
      │     셀 분류, import 추론
      │
      └── [파일 생성 엔진]
            AST 파싱 + 템플릿 렌더링
```

---

## 7. 기술 스택

| 레이어 | 선택 | 이유 |
|---|---|---|
| Frontend | Next.js + Tailwind | 빠른 UI 구성 |
| 그래프 시각화 | React Flow | 노드/엣지 표현에 최적 |
| Backend | FastAPI (Python) | 노트북 파싱이 Python 생태계 |
| LLM | Claude Sonnet 4.6 | 코드 이해 정확도 |
| AST 파싱 | Python `ast` 모듈 | 표준 라이브러리, 별도 의존성 없음 |
| ZIP 생성 | Python `zipfile` | 표준 라이브러리 |
| 배포 | Vercel (FE) + Railway (BE) | 무료 티어로 MVP 운영 가능 |

---

## 8. 사용자 플로우

```
1. 랜딩 페이지 접속
      ↓
2. .ipynb 드래그앤드롭 업로드
      ↓
3. LLM 분석 중... (로딩 스피너, 약 5~15초)
      ↓
4. 결과 화면:
   ┌──────────────────┬───────────────────────┐
   │  셀 분류 결과    │  파일 구조 트리       │
   │  (태그 뱃지)     │  의존성 그래프        │
   └──────────────────┴───────────────────────┘
      ↓
5. 미리보기에서 파일별 코드 확인
      ↓
6. "패키지 다운로드" 버튼 → ZIP 수신
```

---

## 9. 성공 지표 (MVP 기준)

| 지표 | 목표 |
|---|---|
| 셀 분류 정확도 | ≥ 85% (사람이 직접 분류한 것과 비교) |
| import 자동 연결 성공률 | ≥ 80% |
| 처리 시간 | 62-cell 노트북 기준 ≤ 20초 |
| 다운로드 후 실행 성공률 | ≥ 70% (python -c "import myproject" 통과) |
| 주간 활성 사용자 | 런칭 1개월 후 100명 |

---

## 10. 로드맵

```
v0.1 (MVP) — 4주
  ✓ 업로드 → 분류 → ZIP 다운로드 핵심 플로우
  ✓ 의존성 그래프 시각화
  ✓ import 자동 연결

v0.2 — 8주
  + GitHub 직접 PR 생성
  + 자동 테스트 코드 생성 (pytest)
  + 분류 결과 수동 수정 UI

v0.3 — 12주
  + 팀 워크스페이스
  + 노트북 버전 비교 (diff)
  + CLI 도구 연동 (nbrefactor 호환)

v1.0
  + CI/CD 파이프라인 자동 생성
  + Docker/requirements.txt 자동 생성
  + 엔터프라이즈 플랜 (온프레미스)
```

---

## 11. 레퍼런스

| 논문/도구 | 참조 내용 |
|---|---|
| MASA (arXiv:2511.07257) | 멀티에이전트 노트북 변환 파이프라인 구조 |
| CodeAlchemist | Notebook Converter 96% 정확도 접근법 |
| Soorgeon (Ploomber) | 노트북 → 파이프라인 변환 UX 참조 |
| nbrefactor | AST 기반 의존성 분석 방법론 |
| CMU-CS-22-123 | 함수 추출 및 셀 경계 탐지 기법 |
