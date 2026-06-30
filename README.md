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
[상단]  파일 노드         ← "어떤 파일들이 있는가"
          │  contains
[중간]  함수 / 클래스     ← "어떤 기능 단위가 있는가"  (클릭 → 소스코드)
          │  imports (점선)
[하단]  외부 의존성       ← "무엇에 의존하고 있는가"
```

---

## 관련 문서

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — Mermaid ERD + 파이프라인 다이어그램
- [`MVP_DESIGN.md`](MVP_DESIGN.md) — 제품 설계, 시장 분석, 로드맵
- [`extension/graph_output/graph.html`](extension/graph_output/graph.html) — 실제 생성된 의존성 그래프 예시
