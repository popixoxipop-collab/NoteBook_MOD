# HANDOFF — NoteBook_MOD

**Repo**: `popixoxipop-collab/NoteBook_MOD`  
**Branch**: `main`  
**Last commit**: `389eb216` fix(graph-html): escape `</script>` in JSON  
**Date**: 2026-06-30  

---

## 1분 요약

**NoteBook_MOD**는 GitHub 레포를 스캔해 "언어별 의존성 그래프"를 생성하는 엔진이다.  
출력은 Why Depth Engine(코드 이해도 인증 시스템)의 입력 데이터로 쓰인다.

```
레포 스캔 → AST/regex 파서 → DependencyGraph → graph.json / graph.html / graph.canvas
```

MVP 기준 **Python · JS/TS · Java · C** 파서 구현 완료. 261 노드 / 726 엣지 (자체 레포 스캔 기준).

---

## 파일 맵

```
NoteBook_MOD/
├── README.md                          ← B2B 피치 + 설계 철학 (공개용)
├── HANDOFF.md                         ← 이 파일 (인수인계용)
├── ARCHITECTURE.md                    ← Mermaid ERD + 파이프라인 다이어그램
├── MVP_DESIGN.md                      ← 제품 설계, 시장 분석, 로드맵
│
└── extension/
    └── graph_exporter/
        ├── cli.py                     ← 진입점 (scan + query 서브커맨드)
        ├── common.py                  ← DependencyGraph, GraphNode, GraphEdge 데이터클래스
        ├── version_resolver.py        ← manifest 파싱 → import 노드 버전 주석
        ├── query.py                   ← keyword search over graph.json (D5)
        ├── parsers/
        │   ├── python_parser.py       ← ast 모듈 기반 (함수/클래스/import)
        │   ├── js_parser.py           ← regex (ES6 import/export, function)
        │   ├── java_parser.py         ← regex (import, class, method)
        │   └── c_parser.py            ← regex (#include, function signature)
        └── exporters/
            ├── html_preview.py        ← vis.js 계층형 HTML (D6) ← 최근 대폭 수정
            └── obsidian_canvas.py     ← Obsidian Canvas JSON

    └── graph_output/                  ← 생성물 (커밋에 포함됨)
        ├── graph.html                 ← 인터랙티브 그래프
        ├── graph.json                 ← raw 노드/엣지
        └── graph.canvas               ← Obsidian Vault 전용
```

---

## 실행 방법

```bash
# 전체 스캔 + 전체 출력 생성
cd extension
python3 -m graph_exporter.cli . --out graph_output --title "NoteBook_MOD"

# 그래프 키워드 검색 (토큰 절약)
python3 -m graph_exporter.cli query "version resolver" --out graph_output -k 20
```

브라우저에서 바로 열기:
```bash
open extension/graph_output/graph.html
```

---

## 설계 결정 목록 (D[N])

| ID | 결정 | WHY | COST | EXIT |
|----|------|-----|------|------|
| **D1** | cross-file call resolve — 2-pass name-based | Python 파서가 `{file}::{name}`만 생성. 크로스 파일 호출 누락 | 동명 함수가 여러 파일에 있으면 fan-out (false edge) | import-graph resolver로 교체 |
| **D2** | source_code를 HTML에 임베딩 | 함수 클릭 시 소스코드 패널 → CDN 없이 self-contained | 237KB → 1.2MB (5×) | Fetch API로 원본 파일 로드 |
| **D3** | import 노드를 레이어 최상단 배치 | "먼저 설치해야 하는 것"이 먼저 보이는 독해 순서 | imports 엣지가 아래→위 역방향처럼 보임 | 순서 교체는 level 값만 수정 |
| **D4** | manifest 버전 파싱 (best-effort) | lockfile 없이도 선언 버전 표시 가능 | 범위 지정(`>=1.0`) 이 남을 수 있음 | poetry.lock / yarn.lock 파서로 교체 |
| **D5** | keyword-based graph query | graph.json 전체 = 50K+ 토큰; 쿼리 결과만 = ~1-2K | 동의어/오타 미스, 임베딩 없음 | sentence-transformers cosine sim으로 교체 |
| **D6** | vis.js hierarchical UD over D3 custom | D3 x/y 수동 계산 200+ LOC → vis.js level 0/1/2로 대체 | CDN 의존성 (vis-network@9.1.6, ~800KB) | local bundled copy; cytoscape.js |

---

## 그래프 노드/엣지 스키마

```python
@dataclass
class GraphNode:
    id: str            # 고유 식별자 (파일 경로 or "import::name" or "file::name")
    kind: str          # "file" | "import" | "function" | "class" | "variable"
    label: str         # 표시 이름
    file: str          # 소속 파일 경로
    line: int          # 선언 라인
    language: str      # "python" | "javascript" | "java" | "c"
    source_code: str   # 함수/클래스 전체 소스 텍스트
    version: str       # import 노드만: manifest에서 파싱한 버전 (없으면 "")

@dataclass
class GraphEdge:
    source: str        # 출발 노드 id
    target: str        # 도착 노드 id
    kind: str          # "contains" | "imports" | "calls" | "uses"
```

**엣지 의미**:
- `contains`: 파일 → 함수/클래스 (소속)
- `imports`: 파일 → 외부의존성 (import 문)
- `calls`: 함수 → 함수 (호출)
- `uses`: 기타 참조

---

## 완료 항목

- [x] Python / JS / Java / C 파서 (멀티언어 AST + regex 혼합)
- [x] cross-file call resolve (2-pass name matching)
- [x] version_resolver: requirements.txt / package.json / pom.xml / build.gradle
- [x] Obsidian Canvas 출력
- [x] vis.js 계층형 HTML (3-tier: import → file → symbol)
- [x] 함수/클래스 클릭 → 소스코드 패널 (Highlight.js)
- [x] `graph_exporter query` 서브커맨드 (keyword search, 1-hop neighbor)
- [x] README: B2B 피치, ERD vs 그래프 비교, Hook 5종, 이력 기반 학습 섹션

---

## 미완료 / 다음 세션

### 우선순위 높음

| 항목 | 내용 |
|------|------|
| Hook 실제 구현 | README에 코드 예시만 있음. `.claude/hooks/*.py` 파일로 실제 생성 필요 |
| Python 버전 미확인 | `requirements.txt` 없는 레포에서 Python import 버전 0%. PyPI API 조회 추가 고려 |
| vis.js canvas headless 미렌더링 | 스크린샷 자동화에서 canvas가 blank. GPU 없는 환경 한계. 정적 PNG 생성기(matplotlib)는 별도 구현됨 |

### 우선순위 보통

| 항목 | 내용 |
|------|------|
| CI 자동 재생성 | `git push` 시 GitHub Actions에서 `graph_exporter.cli` 실행 → graph_output 자동 커밋 |
| TypeScript 타입 import 파싱 | `import type { Foo }` 현재 일반 import와 동일 취급 |
| calls 정확도 개선 | 동명 함수 fan-out 문제 (D1). import-graph 기반 해결 필요 |
| `uses` 엣지 추가 | 현재 contains/imports/calls만 있음. 변수 참조(`uses`) 엣지 미구현 |

---

## 알려진 버그 / 주의사항

### 1. `</script>` in source_code (수정됨 — 389eb216)
**증상**: graph.html 열면 `#net` div가 비어있고 vis.js가 실행 안 됨  
**원인**: `html_preview.py` 자체 소스코드(템플릿에 `</script>` 포함)가 META JSON에 임베딩되면서 `<script>` 태그 조기 종료  
**수정**: `_safe_json()` 함수로 `</` → `<\/` 치환 (JSON 스펙 유효)  
**교훈**: 소스코드를 `<script>` 블록 안 JSON에 임베딩할 때는 반드시 `<\/` 이스케이프 필요

### 2. vis.js `sortMethod: 'directed'` level 무시 (수정됨 — 114f99b3)
**증상**: 그래프가 뷰포트 밖으로 날아가 blank 처럼 보임  
**원인**: `sortMethod: 'directed'` 는 explicit `level` 속성을 무시하고 엣지 방향으로 재계산. imports 엣지(file→import, level 1→0)가 역방향이라 레이아웃 폭발  
**수정**: `sortMethod: 'hubsize'` 로 교체 → explicit level 존중

### 3. Python frozen runpy warning
**증상**: `python3 -m graph_exporter.cli` 실행 시 RuntimeWarning 출력  
**원인**: `extension/` 안에서 실행 시 패키지 import 충돌  
**영향**: 기능 정상, 경고만 출력 (무시해도 됨)  
**해결**: `cd extension && python3 -m graph_exporter.cli`로 실행

---

## Hook 구현 현황

README에 코드 예시로만 존재. 실제 파일 미생성.

| Hook | 위치 (예정) | 상태 |
|------|------------|------|
| `api-route-guard.py` | `.claude/hooks/api-route-guard.py` | 📄 README 예시만 |
| `graph-stale-guard.py` | `.claude/hooks/graph-stale-guard.py` | 📄 README 예시만 |
| `version-coverage-guard.py` | `.claude/hooks/version-coverage-guard.py` | 📄 README 예시만 |
| `decision-log-guard.py` | `.claude/hooks/decision-log-guard.py` | 📄 README 예시만 |
| `high-fanin-warn.py` | `.claude/hooks/high-fanin-warn.py` | 📄 README 예시만 |

Hook을 실제로 쓰려면 위 경로에 파일을 생성하고 `~/.claude/settings.json`의 `hooks` 섹션에 등록해야 한다.

---

## 세션 커밋 이력

| 커밋 | 내용 |
|------|------|
| `8f85cf7` | graph_exporter 초기 구현 (이전 세션) |
| `349974d0` | imports top layer + version badge |
| `22fc0298` | docs: Code with Hook 5종 README 추가 |
| `6cd8352b` | feat: graph query 서브커맨드 (query.py) |
| `02e67526` | docs: ERD vs 그래프 비교 섹션 |
| `1e095902` | docs: 이력 기반 Hook 자동 학습 섹션 |
| `114f99b3` | feat: D3 SVG → vis.js hierarchical layout (D6) |
| `389eb216` | fix: `</script>` in JSON — HTML parser break |

---

## Why Depth Engine 연결 지점

```
graph.json 필드 중 Why Depth Engine이 사용하는 것:

nodes[].kind == "import"   → "왜 이 라이브러리를 사용했는가?" 질문 생성
nodes[].kind == "function" → "이 함수의 역할은?" / "대안 설계는?" 질문 생성
edges[].kind == "calls"    → 호출 체인 파악 → "병목 지점은?" 질문 생성
fan-in 높은 노드           → "이 모듈이 단일 장애점인 이유는?" 질문 생성
edges[].kind == "contains" → 파일-심볼 소속 파악 → 기여도 분석에 사용
```

**현재 연결 상태**: 미연결 (graph.json 생성만 됨, Why Depth Engine은 별도 레포)
