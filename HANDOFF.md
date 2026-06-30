# HANDOFF — NoteBook_MOD

**Repo**: `popixoxipop-collab/NoteBook_MOD` · **Branch**: `main` · **Commit**: `bd3b82a7`  
**Date**: 2026-06-30 · **담당**: popixoxipop

---

## 프로젝트 한 줄 정의

> GitHub 레포를 스캔해 **언어별 의존성 그래프**를 생성하고,  
> "왜 이렇게 설계했는가"를 검증하는 Why Depth Engine의 입력 데이터를 만든다.

---

## 핵심 기능 요약

### 1. 왜 의존성 그래프인가

AI가 코드를 대신 짜주는 시대에는 코드 구현이 아닌 **구조적 연결의 이유**를 검증해야 한다.

| 검증 목표 | 의존성 그래프 없이 | 의존성 그래프 있을 때 |
|---|---|---|
| 설계 이해 | "이 함수 설명해보세요" | "Y가 X와 Z 사이에 위치한 이유가 뭔가요?" |
| 영향 범위 | 판단 불가 | "Y를 수정하면 어떤 파일이 영향받나요?" |
| 병목 지점 | 판단 불가 | "호출 체인에서 가장 무거운 지점은?" |
| 대안 설계 | 임의 생성 | "캐시를 넣는다면 어느 계층에 넣겠어요?" |

**실증 근거**
- [arXiv:2603.27277 — Codebase-Memory](https://arxiv.org/abs/2603.27277): 31개 레포 측정, 파일 탐색 대비 **토큰 10×감소 / tool call 2.1×감소**
- [arXiv:2404.16130 — GraphRAG](https://arxiv.org/abs/2404.16130): Microsoft Research, 그래프 기반 쿼리의 이점 정량화
- [arXiv:2505.16901 — Code Graph Model](https://arxiv.org/pdf/2505.16901): 코드 토큰을 그래프 노드로 압축, LLM 유효 컨텍스트 **512×확장**

---

### 2. ERD·API 명세와의 차이

> "계약서가 아니라 지문이다. 코드가 진실이면 그래프도 진실이다."

| 질문 | ERD | ERD+API명세 | 의존성 그래프 |
|---|---|---|---|
| 데이터 저장 구조 | ✅ | ✅ | ✅ |
| API 엔드포인트 목록 | ❌ | ✅ | ✅ |
| 명세↔구현 일치 여부 | ❌ | ❌ | ✅ 자동 검출 |
| 함수 fan-in (어디서 호출되나) | ❌ | ❌ | ✅ |
| 수정 영향 범위 | ❌ | ❌ | ✅ |
| 단일 장애점(SPOF) | ❌ | ❌ | ✅ |
| 외부 의존성 버전 충돌 | ❌ | ❌ | ✅ manifest 파싱 |

**실제 발생한 버그** (이 레포에서 직접 확인):
```
OpenAPI 명세:  POST /api/confirm   ← 문서에 존재
실제 라우트:    route("/state")     ← 코드에 등록된 경로
→ stateStore.ts의 /confirm fetch → 런타임 404
→ 명세는 틀렸지만 그래프에서는 자동 검출 가능
```

---

### 3. 언어별 파서

현실 레포는 단일 언어가 아니다. `checkout.tsx → /api/payment → PaymentService.java → score.py` 같은 크로스 언어 흐름을 추적하기 위해 언어별로 파서를 분리한다.

| 언어 | 파서 방식 | 근거 |
|---|---|---|
| Python | `ast` 모듈 (표준) | 들여쓰기 기반 — 정규식으로 블록 경계 판단 불가 |
| JS / TS | regex (ES6 import/export) | 동적 `require` 혼재 — 정적 AST가 오히려 복잡 |
| Java | regex (import·class·method) | 패키지 경로가 곧 의존성 — 선언문 파싱으로 충분 |
| C / C++ | regex (`#include`, 함수 시그니처) | 전처리기 매크로로 AST 불안정 — regex가 현실적 |

---

### 4. 출력물

```bash
cd extension
python3 -m graph_exporter.cli . --out graph_output --title "NoteBook_MOD"
```

| 파일 | 내용 |
|---|---|
| `graph.html` | vis.js 계층형 인터랙티브 그래프 (함수 클릭 → 소스코드 패널) |
| `graph.canvas` | Obsidian Vault에 복사해서 열기 |
| `graph.json` | Why Depth Engine 입력용 raw 노드/엣지 데이터 |

**HTML 레이어 구조**
```
[최상단 level=0]  외부 의존성 (diamond, 주황)   ← "먼저 설치해야 하는 것"
                        ↑ imports
[중간   level=1]  파일 노드        (box, 파랑)   ← "어떤 파일들이 있는가"
                        ↓ contains
[하단   level=2]  함수 / 클래스    (dot/ellipse)  ← 클릭 → 소스코드 패널
```

**버전 추출 지원**: `requirements.txt` / `pyproject.toml` / `package.json` / `pom.xml` / `build.gradle`

**키워드 검색** (토큰 절약):
```bash
python3 -m graph_exporter.cli query "version resolver" --out graph_output -k 20
# 결과: 261노드 전체(50K+토큰) → 관련 노드 14개(~1-2K토큰) — 125×감소
```

---

### 5. Code with Hook — 구조적 강제

> 규칙을 문서에 적어두면 잊어버린다. 코드로 강제하면 잊어버릴 수 없다.

```
시행착오 발생 → 원인 분석 → 규칙 문서화 → Hook 코드화
                                    ↑ 여기서 멈추면 또 잊어버린다
```

| Hook | 트리거 | 수준 | 해결한 시행착오 |
|---|---|---|---|
| `api-route-guard` | stateStore.ts 수정 | 🔴 BLOCK | URL 불일치 → 런타임 전 기능 404 |
| `graph-stale-guard` | git commit/push | 🟡 WARN | 코드 변경 후 그래프 미재생성 커밋 |
| `version-coverage-guard` | graph_exporter 실행 후 | 🟡 WARN | 92% 버전 미확인 → 충돌 감지 무력화 |
| `decision-log-guard` | git commit | 🟡 WARN | 설계 결정이 채팅에만 존재 |
| `high-fanin-warn` | graph_exporter 실행 후 | 🔵 INFO | SPOF 인식 못하고 개발 진행 |

**원칙**: BLOCK은 "통과 시 반드시 문제 발생"인 경우만. 과도한 차단은 hook을 끄게 만든다.

**근거** — [arXiv:2603.18059 — Guardrails as Infrastructure](https://arxiv.org/html/2603.18059v1):
| Policy | 오남용 방지율 | Task 성공률 |
|---|---|---|
| 허용적 (P1) | 0.000 | 0.356 |
| 엄격 (P4) | 0.681 | **0.067** |
→ 모든 규칙을 BLOCK으로 시작하면 task success 18% 수준으로 붕괴. WARN→BLOCK 점진 승격이 이유.

---

### 6. 이력 기반 Hook 자동 학습

> 기존 린터는 범용 규칙을 제공한다. 이 시스템은 **이 팀이 실제로 반복한 실수**에서 규칙을 추출한다.

```
hook 발동 로그 → 패턴 추출 → 실수 빈도 맵 → 임계값 도달 시 WARN→BLOCK 자동 승격
                                                      ↓
                                              그래프 쿼리로 유사 패턴 파일 탐색
                                                      ↓
                                              개인화된 가드레일 → 재귀적 업데이트
```

| | 기존 린터 | 팀 커스텀 lint | 이 시스템 |
|---|---|---|---|
| 규칙 출처 | 커뮤니티 범용 | 팀이 수동 작성 | **실수 이력에서 자동 추출** |
| 업데이트 방식 | 버전 릴리스 | 사람이 편집 | **발동 빈도 기반 자동 재보정** |
| 컨텍스트 인식 | 없음 | 없음 | **의존성 그래프로 영향 범위 파악** |
| 강도 조절 | on/off | on/off | **WARN→BLOCK 점진적 승격** |

**그래프 쿼리 효율 근거**:
- [safishamsi/graphify](https://github.com/safishamsi/graphify): Tree-Sitter AST → KG → BFS 서브그래프. 자체 F-CORE 레포 측정 **11.5×토큰 절감**
- [arXiv:2505.16901 — Code Graph Model](https://arxiv.org/pdf/2505.16901): 코드 그래프 노드 압축 512× 컨텍스트 확장

---

## 설계 결정 (D[N])

| ID | 결정 | WHY | COST | EXIT |
|----|------|-----|------|------|
| D1 | cross-file call 2-pass resolve | 크로스 파일 호출 누락 방지 | 동명 함수 fan-out (false edge) | import-graph resolver |
| D2 | source_code HTML 임베딩 | self-contained, CDN 불필요 | 1.2MB (5×) | Fetch API |
| D3 | import 최상단 level=0 | 설치 선행 조건이 먼저 보임 | imports 엣지 역방향처럼 보임 | level 값만 수정 |
| D4 | manifest 버전 best-effort | lockfile 없이도 버전 표시 | 범위 지정(`>=1.0`) 잔존 | poetry.lock/yarn.lock 파서 |
| D5 | keyword graph query | 50K+토큰 → 1-2K (125×) | 동의어/오타 미스 | sentence-transformers |
| D6 | vis.js hierarchical UD | D3 x/y 200+LOC 제거 | CDN ~800KB | local bundle |

---

## 알려진 버그 (수정 이력 포함)

### ① `</script>` in source_code — **수정완료** (`389eb216`)
- **증상**: graph.html 열면 `#net` div 비어있음, vis.js 미실행
- **원인**: `html_preview.py` 소스코드(템플릿에 `</script>` 포함)가 META JSON에 임베딩 → `<script>` 태그 조기 종료 → JS 전체 파싱 실패
- **수정**: `_safe_json()` 함수 — `</` → `<\/` 치환 (`\/` = JSON 유효 이스케이프)
- **교훈**: 소스코드를 `<script>` 블록 내 JSON에 임베딩 시 반드시 `<\/` 이스케이프

### ② vis.js `sortMethod: 'directed'` level 무시 — **수정완료** (`114f99b3`)
- **증상**: 그래프 blank (뷰포트 밖으로 날아감)
- **원인**: `directed` 모드는 explicit `level` 무시, 엣지 방향으로 재계산. imports 엣지(file→import, level 1→0 역방향)가 레이아웃 폭발
- **수정**: `sortMethod: 'hubsize'` → explicit level 존중

### ③ headless Chrome canvas 미렌더링 — **미해결**
- vis.js는 canvas 기반. GPU 없는 headless에서 `requestAnimationFrame` 미동작
- 정적 스크린샷은 matplotlib 기반 PNG 생성기로 대체 (`/tmp/graph_static2.png`)

---

## 미완료 항목

| 우선순위 | 항목 | 세부 내용 |
|---------|------|----------|
| 🔴 높음 | Hook 실제 파일 생성 | README 코드 예시를 `.claude/hooks/*.py`로 실제 생성 + `settings.json` 등록 |
| 🔴 높음 | Python 버전 미확인 | `requirements.txt` 없는 레포 = 버전 0%. PyPI API 조회 추가 |
| 🟡 보통 | CI 자동 재생성 | GitHub Actions에서 push 시 graph_output 자동 갱신 |
| 🟡 보통 | calls 정확도 | 동명 함수 fan-out (D1). import-graph resolver 필요 |
| 🟢 낮음 | `uses` 엣지 | 변수 참조 엣지 미구현 |
| 🟢 낮음 | TypeScript type import | `import type { Foo }` = 일반 import와 동일 취급 중 |

---

## 커밋 이력

| 커밋 | 내용 |
|------|------|
| `8f85cf7` | graph_exporter 초기 구현 (이전 세션) |
| `349974d0` | imports top layer + version badge |
| `22fc0298` | docs: Code with Hook 5종 |
| `6cd8352b` | feat: graph query 서브커맨드 (D5) |
| `02e67526` | docs: ERD vs 그래프 비교 섹션 |
| `1e095902` | docs: 이력 기반 Hook 자동 학습 섹션 |
| `114f99b3` | feat: D3 → vis.js hierarchical (D6) |
| `389eb216` | fix: `</script>` JSON 이스케이프 |
| `bd3b82a7` | docs: HANDOFF.md 최초 작성 |

---

## Why Depth Engine 연결 지점 (미연결)

```
graph.json 노드/엣지 → Why Depth Engine 질문 생성

nodes[kind=import]    → "왜 이 라이브러리를 선택했는가?"
nodes[kind=function]  → "이 함수를 대안 위치에 놓을 수 없었는가?"
edges[kind=calls]     → 호출 체인 파악 → "병목 지점은?"
fan-in 높은 노드       → "이 모듈이 단일 장애점인 이유는?"
```

현재 상태: graph.json 생성만 완료. Why Depth Engine은 별도 레포 (미연결).
