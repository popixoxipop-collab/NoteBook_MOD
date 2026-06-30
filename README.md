# NoteBook_MOD

> **Jupyter Notebook 자동 모듈화 + 코드 의존성 시각화 도구**  
> [Depth-of-Why](https://github.com/popixoxipop-collab) 플랫폼의 백엔드 분석 컴포넌트

---

## 한 줄 요약

62셀짜리 Jupyter Notebook을 업로드하면 LLM이 셀을 분석·분류해 **Python 패키지 구조**로 분리하고, 함수 간 호출 의존성을 **인터랙티브 그래프**로 시각화한다.

---

## 배경: 왜 만들었나

```
# 현실의 노트북 (예시: 62 cells, 모든 코드 혼재)
ReviewState       ←─ 데이터 구조
analyzer_node     ←─ 분석 로직      } 한 파일에 전부
critic_node       ←─ 검증 로직
DB 연결·저장 코드
Streamlit UI 코드
실행 테스트 코드
```

`nbconvert`는 한 덩어리 `.py`로 변환할 뿐 구조 분리를 하지 않는다.  
"노트북 업로드 → 자동 모듈화 → 패키지 export" 웹 서비스는 현재 공백 시장이다.

---

## 프로젝트 구조

```
NoteBook_MOD/
├── extension/
│   ├── notebook_mod/          # JupyterLab 서버 익스텐션 (Python)
│   │   ├── __init__.py        # 라우트 등록: /analyze /state /categories
│   │   ├── handlers.py        # 3단계 분류 파이프라인 + REST 핸들러
│   │   ├── llm_classifier.py  # OpenAI gpt-4o-mini 분류기
│   │   └── state_db.py        # SQLite StateDB (확정 매핑 캐시)
│   │
│   ├── src/                   # JupyterLab 프론트엔드 익스텐션 (TypeScript)
│   │   ├── index.ts           # 익스텐션 진입점
│   │   ├── viewPlugin.ts      # CodeMirror 6 뷰 플러그인
│   │   ├── badge.ts           # 함수/클래스 뱃지 위젯
│   │   ├── stateStore.ts      # 백엔드 API 클라이언트
│   │   ├── correctionWidget.ts# 사용자 수정 UI
│   │   ├── algorithm.ts       # 분류 알고리즘 (프론트 레이어)
│   │   └── metadata.ts        # 셀 메타데이터 읽기/쓰기
│   │
│   ├── graph_exporter/        # 멀티언어 의존성 그래프 추출기 (신규)
│   │   ├── common.py          # GraphNode / GraphEdge / DependencyGraph 공통 스키마
│   │   ├── cli.py             # CLI 진입점
│   │   ├── parsers/
│   │   │   ├── python_parser.py  # ast 기반 (import/def/class/call)
│   │   │   ├── js_parser.py      # regex 기반 (ES6 import, function, class)
│   │   │   ├── java_parser.py    # regex 기반 (import, class, method)
│   │   │   └── c_parser.py       # regex 기반 (#include, function)
│   │   └── exporters/
│   │       ├── obsidian_canvas.py # Obsidian .canvas JSON 생성
│   │       └── html_preview.py    # D3.js 계층형 인터랙티브 HTML
│   │
│   ├── graph_output/          # 생성된 그래프 결과물 (커밋 포함)
│   │   ├── graph.html         # 브라우저 미리보기 (D3.js, self-contained)
│   │   ├── graph.canvas       # Obsidian Canvas (Vault에 복사해서 열기)
│   │   └── graph.json         # 원시 노드/엣지 JSON
│   │
│   ├── agents/                # LangGraph 에이전트 노드 예시
│   ├── graph/                 # LangGraph StateGraph 빌더
│   ├── db/                    # SQLite 초기화·저장 유틸
│   └── utils/                 # API 키 로드, LLM 팩토리
│
├── ARCHITECTURE.md            # Mermaid ERD + 파이프라인 + 의존성 다이어그램
└── MVP_DESIGN.md              # 제품 설계 문서 (v0.1 범위, 로드맵)
```

---

## 핵심 기능

### 1. 3단계 셀 분류 파이프라인

```
함수/클래스 감지 (regex)
        │
        ▼
  ┌─────────────────────────────────────┐
  │  Tier 1: StateDB 캐시 hit?          │──YES──→ 즉시 반환 (confidence=1.0)
  └─────────────────────────────────────┘
        │NO
        ▼
  ┌─────────────────────────────────────┐
  │  Tier 2: OpenAI gpt-4o-mini        │──OK───→ source='llm'
  │   few-shot: 확정 매핑 + 수정 이력   │
  └─────────────────────────────────────┘
        │실패/키 없음
        ▼
  ┌─────────────────────────────────────┐
  │  Tier 3: 규칙 기반 fallback         │
  │   sentence-transformers / TF-IDF   │──→ source='fallback'
  │   cosine 유사도 greedy 클러스터링   │
  └─────────────────────────────────────┘
```

### 2. Human-in-the-Loop 수정 플라이휠

사용자가 잘못된 분류를 수정하면 `corrections` 테이블에 기록되고,
다음 LLM 호출의 few-shot 예시로 자동 주입된다.
수정이 쌓일수록 같은 프로젝트에서 캐시 hit率이 높아진다.

### 3. JupyterLab 인라인 뱃지 뷰어

CodeMirror 6 `StateField` + `Decoration.replace({ block: true })`로
함수/클래스 코드 블록을 뱃지로 축소한다.

```
[Before]                          [After]
def analyzer_node(state):    →   def 📄 analyzer_node
    review = state["review"]          ↑ hover → 원본 코드 팝오버
    ...                               ↑ click → .py 파일 오픈
```

### 4. 멀티언어 의존성 그래프 (`graph_exporter`)

Python · JavaScript/TypeScript · Java · C/C++ 소스를 스캔해  
공통 노드/엣지 스키마로 추출하고 두 가지 포맷으로 내보낸다.

| 포맷 | 용도 |
|------|------|
| `graph.html` | 브라우저에서 즉시 열기 (D3.js 계층형 포스 그래프) |
| `graph.canvas` | Obsidian Vault에 복사 → Canvas 뷰 |
| `graph.json` | raw JSON, 다른 툴 연동용 |

---

## REST API (JupyterLab 서버 익스텐션)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET`  | `/notebook-mod/analyze` | 현재 StateDB 매핑 전체 반환 |
| `POST` | `/notebook-mod/analyze` | 노트북 셀 분석·분류 실행 |
| `GET`  | `/notebook-mod/state`   | 카테고리·매핑 통합 반환 |
| `POST` | `/notebook-mod/state`   | 매핑 확정(`confirm`) 또는 수정(`correct`) |
| `GET`  | `/notebook-mod/categories` | 카테고리 목록 반환 |
| `POST` | `/notebook-mod/categories` | 카테고리 추가(`add`) |

---

## 의존성 그래프 CLI 사용법

```bash
# 설치
pip install -e extension/

# 스캔 실행 (현재 디렉토리 기준)
python -m graph_exporter.cli . --out graph_output --title "MyProject"

# 결과물
# graph_output/graph.html    ← 브라우저에서 open
# graph_output/graph.canvas  ← Obsidian Vault 폴더에 복사
# graph_output/graph.json    ← raw JSON
```

**HTML 그래프 조작법**

| 조작 | 동작 |
|------|------|
| 스크롤 / 핀치 | 줌 인/아웃 |
| 드래그 | 캔버스 이동 |
| 함수 노드 클릭 | 우측 패널에 원본 소스코드 표시 (Highlight.js) |
| `×` 버튼 | 소스코드 패널 닫기 |

**레이아웃 (3-tier 계층형)**

```
[상단] 파일 노드 (파란색)
         │  contains
[중간] 함수(초록 ƒ) / 클래스(보라 ◆)  ←───→ calls 엣지
         │  imports (점선)
[하단] 외부 import 노드 (회색)
```

**지원 언어**

| 언어 | 확장자 | 파서 방식 |
|------|--------|----------|
| Python | `.py` | `ast` 모듈 (정확한 소스코드 추출) |
| JavaScript/TypeScript | `.js .ts .jsx .tsx` | regex (ES6 import, export) |
| Java | `.java` | regex (import, class, method) |
| C / C++ | `.c .cpp .h .hpp` | regex (#include, function) |

---

## 주요 설계 결정 (Decision Log)

| ID | 결정 | WHY | COST | EXIT |
|----|------|-----|------|------|
| D1 | cross-file call 해소: post-scan resolve_calls 패스 | intra-file 매핑만으론 667개 중 523개만 렌더됨 | 동일 이름 함수 fan-out | import-graph 추적 리졸버로 교체 |
| D2 | 소스코드 JSON 임베드 (self-contained HTML) | 서버 없이 파일 하나로 공유 가능 | HTML 크기 240KB→737KB | 백엔드 API `/api/src?id=…` fetch로 교체 |
| D3 | 계층형 레이아웃 (file→symbol→import, top-down) | 파일 소유권이 한눈에 보임; 포스 레이아웃은 계층 숨김 | calls 엣지가 멀리 떨어진 파일 간 호 생성 | `html_preview.py`의 `_LAYOUT_JS` 블록만 교체 |
| D4 | SQLite StateDB (`.nbmod_state.db`) | 외부 의존성 없음, 단일 프로세스 쓰기로 충분 | 동시 쓰기 병목, 수평 확장 불가 | Repository 인터페이스 추상화 → PostgreSQL impl 교체 |
| D5 | 3단계 fallback (StateDB→LLM→규칙) | API 키 없는 환경에서도 동작 | 규칙 기반 정확도는 LLM보다 낮음 | Tier 3을 외부 embedding 서비스로 교체 |

---

## 구현 상태

| 기능 | 상태 |
|------|------|
| 셀 분석·분류 (3-tier) | ✅ 완료 |
| StateDB 확정 매핑 캐시 | ✅ 완료 |
| Human-in-loop 수정 플라이휠 | ✅ 완료 |
| JupyterLab 인라인 뱃지 | ✅ 완료 |
| URL 버그 수정 (stateStore.ts) | ✅ 완료 |
| 멀티언어 의존성 그래프 (graph_exporter) | ✅ 완료 |
| 계층형 HTML 그래프 + 소스코드 패널 | ✅ 완료 |
| Obsidian Canvas 내보내기 | ✅ 완료 |
| ZIP 패키지 다운로드 (F5) | 🔲 미구현 |
| import 자동 연결 (F6) | 🔲 미구현 |

---

## 설치 및 실행

```bash
# Python 익스텐션 설치 (개발 모드)
pip install -e extension/

# JupyterLab 익스텐션 빌드
cd extension && jlpm install && jlpm build

# JupyterLab 실행
jupyter lab
```

**환경 변수**

```bash
OPENAI_API_KEY=sk-...   # Tier 2 LLM 분류에 필요 (없으면 규칙 기반 fallback)
```

---

## 관련 문서

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — Mermaid ERD, 파이프라인, 의존성 다이어그램 (GitHub에서 렌더링)
- [`MVP_DESIGN.md`](MVP_DESIGN.md) — 제품 설계, 시장 분석, 로드맵
- [`extension/graph_output/graph.html`](extension/graph_output/graph.html) — 최신 NoteBook_MOD 의존성 그래프 (브라우저에서 열기)

---

## 참조

| 논문/도구 | 참조 내용 |
|-----------|-----------|
| MASA (arXiv:2511.07257) | 멀티에이전트 노트북 변환 파이프라인 구조 |
| CodeAlchemist | Notebook Converter 96% 정확도 접근법 |
| Soorgeon (Ploomber) | 노트북 → 파이프라인 변환 UX 참조 |
