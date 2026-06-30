# NoteBook_MOD — Depth-of-Why 코드 분석 엔진

> **Depth-of-Why**의 핵심 백엔드 컴포넌트.  
> GitHub 레포를 분석해 "왜 이렇게 짰는가"를 단계적으로 검증하는 AI 인터뷰 엔진.

---

## 제품 개요 — Depth-of-Why란?

> AI 시대에 코드를 "생성"하는 건 누구나 한다. 진짜 역량은 **"왜 이렇게 설계했는가"를 설명할 수 있는가**에 있다.
> Depth-of-Why는 코드 이해도를 7단계 질문 구조로 검증해 인증 리포트를 발행하는 B2B SaaS다.

**선정 배경**

| 시장 신호 | 내용 |
| --- | --- |
| Anthropic RCT | AI 보조 시 학습 이해도 저하 실증 |
| 코딩테스트 부정행위 | 15% → 35% 급증 |
| 무신사 등 현업 전환 | "AI 출력 검증 능력" 중심으로 면접 기준 변화 |
| 도구 공백 | 부트캠프·대학·공공에서 판단 깊이 검증 도구가 없음 |

---

## 1. 목표 고객 (B2B 우선순위)

### 1순위 — 코딩 평가 플랫폼 기업 ⭐⭐⭐⭐⭐

- 예시: 프로그래머스, 그렙(Grepp), 코드트리, 코드잇, 엘리스, 코드스테이츠
- 이들은 채점·제출 기능은 갖췄지만 **"AI 시대의 코드 이해도 검증"** 기능은 없음
- 우리는 채점 플랫폼이 아닌 **평가 모듈 (API/SaaS)** 을 판매하는 포지션

```
프로그래머스 → 기존 코딩테스트 → [NoteBook_MOD API 호출]
                                           │
                                    GitHub 레포 분석
                                           │
                                    Why Depth 검증
                                           │
                                    결과 리포트 반환 → 프로그래머스
```

### 2순위 — 부트캠프 LMS ⭐⭐⭐⭐

- 예시: KT AIVLE, 삼성 SSAFY, 멋쟁이사자처럼, 패스트캠퍼스, 인프런 캠프
- 현재 강사가 "이거 네가 짰어?"를 직접 물어보는 과정을 AI가 대신 수행

### 3순위 — SI 기업 신입 교육센터 ⭐⭐⭐

- 예시: LG CNS, SK AX, 현대오토에버, 포스코DX

---

## 2. 핵심 방법론 — Why Depth Engine

> 단순 질문 생성이 아닌 **"설명의 깊이"를 채점**하는 것이 핵심 차별점.  
> 일반 ChatGPT식 후속 질문과 다른 이유: 단계별 구조 + 루브릭 점수화 알고리즘.

### Depth Ladder (7단계 질문 구조)

| Step | 단계 | 질문 예시 |
| --- | --- | --- |
| 1 | **What** | 이 함수는 무슨 역할인가요? |
| 2 | **How** | 어떻게 동작하나요? |
| 3 | **Why** | 왜 이 방법을 선택했나요? |
| 4 | **Alternative** | 다른 방법은 없었나요? |
| 5 | **Trade-off** | 장단점은 무엇인가요? |
| 6 | **Constraint** | 트래픽이 100배가 되면 어떻게 되나요? |
| 7 | **Reflection** | 다시 만든다면 어떻게 하시겠어요? |

### 깊이 점수 채점 예시

```
"Redis가 빨라서요."
→ 깊이 15점

"상품조회가 반복되고 TTL 30초여도 문제없어서 Redis를 썼습니다."
→ 깊이 72점

"사실 Redis보다 Index 최적화부터 했어야 했습니다." (자기반성 + 대안 인식)
→ 깊이 94점
```

### 전체 파이프라인

```
GitHub Repository 제출
        │
        ▼
코드 구조 분석 (AST, 의존성 그래프, 커밋 이력)   ← NoteBook_MOD
        │
        ▼
Why Map 생성 (핵심 설계 포인트 추출)
        │
        ▼
Why Depth Engine
 ├─ Level 1 : What       (기능 이해)
 ├─ Level 2 : How        (구현 이해)
 ├─ Level 3 : Why        (설계 이유)
 ├─ Level 4 : Alternative(대안 비교)
 ├─ Level 5 : Trade-off  (장단점 분석)
 ├─ Level 6 : Constraint (반례·제약 조건)
 └─ Level 7 : Reflection (개선 및 회고)
        │
        ▼
루브릭 채점 (정확성·근거·대안·트레이드오프)
        │
        ▼
이해도 인증 리포트
```

---

## 3. 서비스 기능 구성

| 기능 | 내용 | 상태 |
| --- | --- | --- |
| **코드 구조 분석** | AST 기반 함수/클래스/의존성 추출 (Python·JS·Java·C) | ✅ 완료 |
| **3단계 분류 파이프라인** | StateDB 캐시 → LLM → 규칙 기반 fallback | ✅ 완료 |
| **의존성 그래프 시각화 (Why Map)** | 파일→함수→import 계층형 그래프, 클릭 시 소스 표시 | ✅ 완료 |
| **Obsidian Canvas 내보내기** | `.canvas` 파일로 Obsidian에서 열기 | ✅ 완료 |
| **JupyterLab 인라인 뱃지** | 함수/클래스를 뱃지로 축소, hover 시 코드 팝오버 | ✅ 완료 |
| **Why Map** | 레포 설계 흐름 시각화 (Spring Security → JWT → … → Repository) | 🔲 예정 |
| **Commit Timeline 분석** | 대량 커밋 시점 집중 검증 | 🔲 예정 |
| **팀 프로젝트 모드** | GitHub Org 분석 → 기여도 파악 → 개인별 질문 분기 | 🔲 예정 |
| **AI 면접관 성향 선택** | 삼성 / 네이버 / 쿠팡 / 스타트업 스타일 | 🔲 예정 |
| **학습 추천** | 미흡 영역 자동 감지 → 강의/문서 추천 | 🔲 예정 |
| **ZIP 패키지 다운로드** | 분리된 `.py` 파일 + `__init__.py` ZIP 출력 | 🔲 예정 |
| **import 자동 연결** | 분리된 파일 간 import 문 자동 생성 | 🔲 예정 |

---

## 4. 기술 구조

### 레포 구성

```
NoteBook_MOD/
├── extension/
│   ├── notebook_mod/          # JupyterLab 서버 익스텐션 (Python)
│   │   ├── handlers.py        # 3단계 분류 파이프라인 REST 핸들러
│   │   ├── llm_classifier.py  # OpenAI gpt-4o-mini 분류기
│   │   └── state_db.py        # SQLite 확정 매핑 캐시
│   │
│   ├── src/                   # JupyterLab 프론트엔드 (TypeScript)
│   │   ├── viewPlugin.ts      # CodeMirror 6 뷰 플러그인
│   │   ├── badge.ts           # 함수/클래스 뱃지 위젯
│   │   └── stateStore.ts      # 백엔드 API 클라이언트
│   │
│   └── graph_exporter/        # 멀티언어 의존성 그래프 추출기
│       ├── parsers/            # Python(ast) · JS(regex) · Java · C/C++
│       └── exporters/          # Obsidian Canvas + D3.js HTML
│
├── ARCHITECTURE.md            # Mermaid ERD + 파이프라인 다이어그램
└── MVP_DESIGN.md              # 제품 설계, 시장 분석, 로드맵
```

### REST API

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `POST` | `/notebook-mod/analyze` | 노트북 셀 분석·분류 실행 |
| `GET` | `/notebook-mod/state` | 카테고리·매핑 통합 반환 |
| `POST` | `/notebook-mod/state` | 매핑 확정(`confirm`) / 수정(`correct`) |
| `GET` | `/notebook-mod/categories` | 카테고리 목록 |
| `POST` | `/notebook-mod/categories` | 카테고리 추가 |

### 분류 파이프라인

```
함수/클래스 감지 (regex)
        │
        ▼ StateDB hit?
  ┌─────YES─────┐         ┌──────────────────────────────────────┐
  │ 즉시 반환   │    NO   │ OpenAI gpt-4o-mini                   │
  │ conf=1.0   │ ───────▶ │ few-shot: 확정 매핑 + 수정 이력 주입 │
  └─────────────┘         └──────────────┬───────────────────────┘
                                         │ 실패/키 없음
                                         ▼
                          ┌──────────────────────────────────────┐
                          │ 규칙 기반 fallback                    │
                          │ sentence-transformers / TF-IDF       │
                          │ cosine 유사도 greedy 클러스터링       │
                          └──────────────────────────────────────┘
```

---

## 5. 의존성 그래프 CLI

```bash
# 설치
pip install -e extension/

# 스캔 실행
python -m graph_exporter.cli . --out graph_output --title "MyProject"
```

**출력물**

| 파일 | 용도 |
| --- | --- |
| `graph.html` | 브라우저 즉시 열기 — D3.js 계층형, 함수 클릭 시 소스코드 표시 |
| `graph.canvas` | Obsidian Vault에 복사 → Canvas 뷰 |
| `graph.json` | raw JSON, 다른 툴 연동용 |

**지원 언어**

| 언어 | 파서 방식 |
| --- | --- |
| Python `.py` | `ast` 모듈 — 정확한 소스코드 추출 |
| JS / TS `.js .ts .jsx .tsx` | regex — ES6 import, export |
| Java `.java` | regex — import, class, method |
| C / C++ `.c .cpp .h .hpp` | regex — #include, function |

---

## 6. 주요 설계 결정

| ID | 결정 | WHY | COST | EXIT |
| --- | --- | --- | --- | --- |
| D1 | cross-file call 해소: post-scan resolve | intra-file 매핑만으론 667개 중 523개만 렌더 | 동일 이름 함수 fan-out | import-graph 추적 리졸버로 교체 |
| D2 | 소스코드 JSON 임베드 | 서버 없이 HTML 파일 하나로 공유 | HTML 240KB → 737KB | 백엔드 API fetch로 교체 |
| D3 | 계층형 레이아웃 (top-down) | 파일 소유권이 한눈에 보임 | calls 엣지가 멀리 호 생성 | `html_preview.py`의 레이아웃 블록만 교체 |
| D4 | SQLite StateDB | 외부 의존성 없음, 단일 프로세스로 충분 | 동시 쓰기 병목, 수평 확장 불가 | Repository 인터페이스 추상화 → PostgreSQL |
| D5 | 3단계 fallback | API 키 없는 환경에서도 동작 보장 | 규칙 기반 정확도 < LLM | Tier 3를 외부 embedding 서비스로 교체 |

---

## 관련 문서

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — Mermaid ERD, 파이프라인, 의존성 다이어그램
- [`MVP_DESIGN.md`](MVP_DESIGN.md) — 제품 설계, 시장 분석, 로드맵
- [`extension/graph_output/graph.html`](extension/graph_output/graph.html) — NoteBook_MOD 자체 의존성 그래프 (브라우저에서 열기)
