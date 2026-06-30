# NoteBook_MOD — Depth-of-Why 코드 분석 엔진

> GitHub 레포를 스캔해 **언어별 의존성 그래프**를 생성하고,  
> "왜 이렇게 설계했는가"를 검증하는 Why Depth Engine의 입력 데이터를 만든다.

---

## 왜 의존성 그래프가 필요한가

> AI가 코드를 대신 짜주는 시대에, 코드 자체를 보는 것만으로는 이해도를 판단할 수 없다.  
> 중요한 건 **"이 코드들이 왜 이런 구조로 연결되어 있는가"** 다.

### 코드만 봐서는 알 수 없는 것들

```
파일 A에 함수 X가 있고, 파일 B에 함수 Y가 있다.

코드 리뷰어가 보는 것:  X의 구현 내용
의존성 그래프가 보여주는 것:  X → Y → Z → 외부 라이브러리 순으로 호출된다
                              → 이 흐름에서 병목은 Y다
                              → Y를 바꾸면 X와 Z 모두 영향받는다
```

**의존성 그래프 없이는 다음 질문을 생성할 수 없다:**

| 검증 목표 | 의존성 그래프 없이 | 의존성 그래프 있을 때 |
| --- | --- | --- |
| 설계 이해 | "이 함수 설명해보세요" | "Y가 X와 Z 사이에 위치한 이유가 뭔가요?" |
| 영향 범위 인식 | 판단 불가 | "Y를 수정하면 어떤 파일이 영향받나요?" |
| 병목 지점 파악 | 판단 불가 | "호출 체인에서 가장 무거운 지점은 어디라고 보나요?" |
| 대안 설계 질문 | 임의 생성 | "여기에 캐시를 넣는다면 어느 계층에 넣겠어요?" |

---

## 왜 언어별로 따로 분석해야 하는가

> 현실의 프로젝트는 단일 언어로 작성되지 않는다.  
> 백엔드(Java/Python)·프론트엔드(TypeScript)·시스템(C/C++)이 섞인 레포가 표준이다.

### 혼합 언어 레포의 실제 구조

```
my-project/
├── backend/          ← Java (Spring)
│   └── service/
│       └── PaymentService.java
├── frontend/         ← TypeScript (React)
│   └── src/
│       └── checkout.tsx
├── ml-pipeline/      ← Python
│   └── score.py
└── native-addon/     ← C++
    └── parser.cpp
```

단일 언어 파서로 분석하면 **3개 레이어의 연결이 보이지 않는다.**  
`checkout.tsx → /api/payment → PaymentService.java → score.py` 흐름을 모르면  
"결제 로직의 병목이 어디인가"를 물을 수 없다.

### 언어별 파서가 다른 이유

| 언어 | 파서 방식 | 이유 |
| --- | --- | --- |
| Python | `ast` 모듈 (표준 라이브러리) | 들여쓰기 기반 문법 — 정규식으로 블록 경계 판단 불가 |
| JS / TS | regex (ES6 import/export 패턴) | 런타임 동적 require가 혼재 — 정적 AST가 오히려 복잡 |
| Java | regex (import·class·method 선언) | 패키지 경로가 곧 의존성 — 선언문 파싱으로 충분 |
| C / C++ | regex (`#include`, 함수 시그니처) | 전처리기 매크로로 AST 파싱이 불안정 — 정규식이 현실적 |

---

## 의존성 그래프가 Why Depth Engine에 연결되는 방식

```
GitHub 레포 제출
      │
      ▼
[언어별 의존성 그래프 생성]        ← NoteBook_MOD
  Python ast + JS regex + Java regex + C regex
      │
      ▼
Why Map 추출
  ┌─ 핵심 호출 체인 파악     (A → B → C → 외부 라이브러리)
  ├─ 높은 결합도 지점 감지   (많은 파일이 의존하는 함수)
  ├─ 외부 의존성 목록        (어떤 라이브러리를 어디서 쓰는가)
  └─ 커밋 이력과 교차 분석   (갑자기 의존성이 늘어난 시점)
      │
      ▼
Why Depth Engine — 그래프 기반 질문 생성
  ├─ Level 3 (Why)       : "Redis를 score.py가 아닌 PaymentService에서 호출한 이유는?"
  ├─ Level 4 (Alternative): "checkout.tsx에서 직접 DB를 쓰지 않은 이유는?"
  ├─ Level 5 (Trade-off)  : "PaymentService 단일 진입점 설계의 단점은?"
  └─ Level 6 (Constraint) : "트래픽 100배 시 이 호출 체인의 어느 지점이 먼저 죽나요?"
      │
      ▼
이해도 인증 리포트
```

---

## B2B 관점에서의 가치

### 코딩 평가 플랫폼이 필요한 이유 ⭐⭐⭐⭐⭐

> 프로그래머스·코드트리 등이 현재 갖고 있는 것: 코드 제출 + 채점  
> 현재 없는 것: **"이 코드를 이해하고 짰는가"** 검증

의존성 그래프가 없으면 AI 생성 코드와 직접 작성 코드를 구별할 기준이 없다.  
AI는 동작하는 코드를 만든다. 하지만 **설계 의도와 의존성 흐름을 설명하지는 못한다.**

```
AI 생성 코드의 특징:
  ✓ 동작한다
  ✓ 스타일이 깔끔하다
  ✗ 왜 이 함수가 여기 있어야 하는지 설명 못 함
  ✗ 의존성 변경 시 영향 범위를 파악하지 못 함

의존성 그래프 기반 질문이 드러내는 것:
  → "이 파일이 왜 저 파일을 import하는가?"
  → "이 함수를 다른 모듈로 옮기면 무엇이 깨지는가?"
```

### 검증 시나리오 비교

| 시나리오 | 기존 코딩테스트 | Depth-of-Why |
| --- | --- | --- |
| AI 대리 제출 | 탐지 어려움 | 의존성 흐름 질문으로 설계 이해 여부 확인 |
| 복붙 코드 | 탐지 어려움 | "이 라이브러리를 왜 선택했나요?" 로 확인 |
| 팀 기여도 불명확 | 판단 불가 | 기여 파일의 의존성 중심으로 개인 질문 분기 |
| 이해 없는 구현 | 통과 가능 | Level 5(Trade-off) 이상에서 확인 |

---

## 출력물

```bash
python -m graph_exporter.cli <레포 경로> --out graph_output
```

| 파일 | 내용 |
| --- | --- |
| `graph.html` | 계층형 인터랙티브 그래프 — 함수 클릭 시 소스코드 패널 표시 |
| `graph.canvas` | Obsidian Vault에 복사해서 열기 |
| `graph.json` | Why Depth Engine 입력용 raw 노드/엣지 데이터 |

**HTML 그래프 레이어 구조**

```
[최상단]  외부 의존성     ← "먼저 설치해야 하는 것" — 버전 표시 (🔶 주황 = 버전 명시)
            ↑  imports (점선, 파일이 위를 향해 참조)
[중간]    파일 노드       ← "어떤 파일들이 있는가"
            ↓  contains
[하단]    함수 / 클래스   ← "어떤 기능 단위가 있는가"  (클릭 → 소스코드)
```

**버전 추출 지원 파일**

| 파일 | 언어 |
| --- | --- |
| `requirements.txt` / `requirements-dev.txt` | Python |
| `pyproject.toml` | Python (Poetry / PEP 621) |
| `package.json` | JavaScript / TypeScript |
| `pom.xml` | Java (Maven) |
| `build.gradle` | Java (Gradle) |

---

## 구조적 강제 — Code with Hook

> 규칙을 문서에 적어두면 잊어버린다. 코드로 강제하면 잊어버릴 수 없다.  
> 이 프로젝트에서 실제로 겪은 시행착오를 hook으로 굳혀서 같은 실수가 반복되지 않게 한다.

### 철학: 시행착오 → 규칙 → Hook

```
시행착오 발생
      │
      ▼
원인 분석 ("왜 이 실수가 반복되는가?")
      │
      ▼
규칙 문서화 (README/주석에 D[N] 형식으로)
      │
      ▼  ← 여기서 멈추면 또 잊어버린다
      ▼
Hook 코드화 (실수가 발생하는 순간에 자동 차단/경고)
```

---

### Hook 1 — API Route Guard

**겪은 시행착오**: `stateStore.ts`가 `/confirm`, `/correct`, `/category`를 호출했지만  
백엔드 `__init__.py`에는 `/state`, `/categories`만 등록돼 있었다.  
빌드 타임에는 에러가 없고, **런타임에야 전 기능 404**로 발견됨.

```python
# .claude/hooks/api-route-guard.py  (PreToolUse: Write|Edit)
# stateStore.ts 수정 시 백엔드 라우트와 URL 정합성 자동 검사

import re, sys, json

tool = json.load(sys.stdin)
path = tool.get("file_path", "")

if "stateStore" not in path:
    sys.exit(0)

content = open(path).read()
# 프론트엔드가 호출하는 URL 추출
fe_urls = set(re.findall(r'fetch\(`\$\{baseUrl\}(/[^`"\']+)', content))

# 백엔드 등록 라우트 추출
init = open("extension/notebook_mod/__init__.py").read()
be_routes = set(re.findall(r'r"/notebook-mod(/[^"]+)"', init))

unmatched = [u for u in fe_urls if not any(u.startswith(r) for r in be_routes)]
if unmatched:
    print(f"[BLOCK] URL 불일치: {unmatched}")
    print(f"  백엔드 등록 라우트: {be_routes}")
    sys.exit(1)
```

| | |
|---|---|
| **WHY** | 런타임 404는 재현하기 전까지 원인을 모름. 빌드 전 차단이 훨씬 싸다 |
| **COST** | 라우트 패턴이 동적이면 false positive 가능 |
| **EXIT** | OpenAPI spec 자동 생성 후 spec 기반 검증으로 교체 |

---

### Hook 2 — Graph Stale Guard

**겪은 시행착오**: 소스 파일을 수정하고 `graph_output/`을 재생성하지 않은 채 커밋.  
의존성 그래프가 코드와 불일치 상태로 GitHub에 올라감.

```python
# .claude/hooks/graph-stale-guard.py  (PreToolUse: Bash — git commit/push 감지)

import sys, json, os, glob
from pathlib import Path

tool = json.load(sys.stdin)
cmd = tool.get("command", "")
if "git commit" not in cmd and "git push" not in cmd:
    sys.exit(0)

src_files = glob.glob("extension/**/*.py", recursive=True) + \
            glob.glob("extension/**/*.ts", recursive=True)
graph_mtime = Path("extension/graph_output/graph.json").stat().st_mtime \
              if Path("extension/graph_output/graph.json").exists() else 0

stale = [f for f in src_files if Path(f).stat().st_mtime > graph_mtime]
if stale:
    print(f"[WARN] 의존성 그래프가 오래됨 — {len(stale)}개 파일이 그래프 생성 후 변경됨")
    print(f"  실행: python -m graph_exporter.cli . --out extension/graph_output")
    print(f"  변경된 파일 (최근 3개): {stale[:3]}")
    # 경고만, 차단은 하지 않음 (의도적 스킵 허용)
```

| | |
|---|---|
| **WHY** | 그래프가 코드와 불일치하면 Why Depth Engine 질문이 틀린 구조를 기반으로 생성됨 |
| **COST** | 경미한 수정 후 매번 재생성 요구는 번거로울 수 있음 → 경고만, 차단 없음 |
| **EXIT** | CI에서 `git diff --stat`로 자동 재생성 후 커밋하는 방식으로 전환 |

---

### Hook 3 — Version Coverage Guard

**겪은 시행착오**: 71개 import 중 65개(92%)가 버전 미확인.  
`requirements.txt`가 없거나 오래돼서 충돌 감지 기능이 사실상 무력화됨.

```python
# .claude/hooks/version-coverage-guard.py  (PostToolUse: Bash — graph_exporter 실행 후)

import sys, json

tool = json.load(sys.stdin)
output = tool.get("output", "")

import re
m = re.search(r"(\d+) resolved / (\d+) unresolved", output)
if not m:
    sys.exit(0)

resolved, unresolved = int(m.group(1)), int(m.group(2))
total = resolved + unresolved
rate = resolved / total if total else 0

if rate < 0.5:
    print(f"[WARN] 버전 해석률 낮음: {resolved}/{total} ({rate:.0%})")
    print("  해결 방법:")
    print("  - Python: requirements.txt 또는 pyproject.toml 추가/업데이트")
    print("  - JS/TS:  package.json dependencies 섹션 확인")
    print("  - Java:   pom.xml 또는 build.gradle 확인")
    print("  버전 명시 없이는 의존성 충돌 감지가 불가능합니다")
```

| | |
|---|---|
| **WHY** | 버전 없는 import 노드는 그래프에서 이름만 보임. 충돌 감지의 핵심이 누락됨 |
| **COST** | 의도적으로 버전을 고정하지 않는 레포(monorepo 등)에서는 노이즈 |
| **EXIT** | lockfile(poetry.lock / yarn.lock) 파서로 교체하면 100% exact version 확보 |

---

### Hook 4 — Decision Log Guard

**겪은 시행착오**: 레이아웃을 바꾸거나 파서 방식을 결정할 때  
이유가 채팅에만 남고 코드에는 기록되지 않음.  
나중에 "왜 이렇게 했지?"를 추적할 수 없었음.

```python
# .claude/hooks/decision-log-guard.py  (PreToolUse: git commit)
# 변경된 파일에 D[N]: 주석이 있는지 확인

import sys, json, subprocess, re

tool = json.load(sys.stdin)
cmd = tool.get("command", "")
if "git commit" not in cmd:
    sys.exit(0)

diff = subprocess.check_output(["git", "diff", "--cached"], text=True)

# 중요 파일 변경 시 Decision 주석 확인
significant = ["parser", "exporter", "handler", "classifier", "layout"]
is_significant = any(k in diff.lower() for k in significant)
has_decision = bool(re.search(r"#\s*D\d+:", diff) or re.search(r"D\d+:", cmd))

if is_significant and not has_decision:
    print("[WARN] 주요 파일 변경에 Decision 주석이 없습니다")
    print("  형식: # D[N]: 결정명")
    print("         #   WHY:  왜 이 선택인가")
    print("         #   COST: 무엇을 포기했나")
    print("         #   EXIT: 어떻게 되돌리나")
    print("  채팅에만 기록하면 컨텍스트 전환 후 추적 불가능합니다")
    # 경고만, 차단 없음
```

| | |
|---|---|
| **WHY** | 결정 이유가 코드에 없으면 3개월 후 본인도 "왜 이렇게 했지?"를 모름 |
| **COST** | 소규모 수정에도 D[N] 작성 압박 → 중요도 필터 필요 (`significant` 리스트 조정) |
| **EXIT** | ADR(Architecture Decision Record) 파일 체계로 전환 시 hook 제거 |

---

### Hook 5 — High Fan-in Warning

**겪은 시행착오**: `state.py`가 모든 모듈에서 import되는 구조였지만  
의존성 그래프를 보기 전까지 파악하지 못함.  
`state.py` 하나가 깨지면 전체가 멈추는 단일 장애점(SPOF)이었음.

```python
# .claude/hooks/high-fanin-warn.py  (PostToolUse: Bash — graph_exporter 실행 후)

import sys, json as jsonlib, re

tool = jsonlib.load(sys.stdin)
output = tool.get("output", "")

# graph.json을 읽어서 높은 fan-in 심볼 감지
import pathlib, json
gf = pathlib.Path("extension/graph_output/graph.json")
if not gf.exists():
    sys.exit(0)

data = json.loads(gf.read_text())
fan_in = {}
for e in data["edges"]:
    if e["kind"] in ("imports", "calls", "contains"):
        fan_in[e["target"]] = fan_in.get(e["target"], 0) + 1

node_by_id = {n["id"]: n for n in data["nodes"]}
hotspots = [(nid, cnt) for nid, cnt in fan_in.items() if cnt >= 5]
hotspots.sort(key=lambda x: -x[1])

if hotspots:
    print(f"[INFO] 고결합도 심볼 (fan-in ≥ 5) — SPOF 위험:")
    for nid, cnt in hotspots[:5]:
        n = node_by_id.get(nid, {})
        label = n.get("label", nid.split("::")[-1])
        print(f"  {label:30s} ← {cnt}개 노드가 의존")
```

| | |
|---|---|
| **WHY** | 높은 fan-in = 수정 시 파급 범위가 큼. 설계 리뷰 전에 인지해야 함 |
| **COST** | 공통 유틸 함수는 원래 fan-in이 높음 → 노이즈 가능 (임계값 조정 필요) |
| **EXIT** | 아키텍처 룰 엔진(ArchUnit 등)으로 교체 시 정책 기반 검사 가능 |

---

### Hook 요약

| Hook | 트리거 | 수준 | 겪은 실수 |
| --- | --- | --- | --- |
| `api-route-guard` | stateStore.ts 수정 | 🔴 차단 | 전 기능 404 (URL 불일치) |
| `graph-stale-guard` | git commit/push | 🟡 경고 | 코드 변경 후 그래프 미재생성 커밋 |
| `version-coverage-guard` | graph_exporter 실행 후 | 🟡 경고 | 92% 버전 미확인 → 충돌 감지 무력화 |
| `decision-log-guard` | git commit | 🟡 경고 | 설계 결정이 채팅에만 존재 |
| `high-fanin-warn` | graph_exporter 실행 후 | 🔵 정보 | SPOF 인식 못 하고 개발 진행 |

> **원칙**: 차단(🔴)은 "이게 통과되면 반드시 문제 발생"인 경우만.  
> 경고(🟡)는 "놓치기 쉬운 것"을 상기시키는 용도. 과도한 차단은 hook을 끄게 만든다.

---

## 관련 문서

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — Mermaid ERD + 파이프라인 다이어그램
- [`MVP_DESIGN.md`](MVP_DESIGN.md) — 제품 설계, 시장 분석, 로드맵
- [`extension/graph_output/graph.html`](extension/graph_output/graph.html) — 실제 생성된 의존성 그래프 예시
