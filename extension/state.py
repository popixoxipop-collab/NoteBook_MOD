from typing import TypedDict, Optional, Dict, Any, Literal


class ReviewState(TypedDict):
    # 입력 리뷰
    review: str

    # 개별 에이전트 실행 결과
    analyzer_result: Optional[Dict[str, Any]]   # {"items":[{"aspect":..., "label":..., "evidence":...}]}
    critic_result:   Optional[Dict[str, Any]]   # {"verdict":"Conformity|Non-conformity", "reason":..., "reason_code":..., "repair_directive":...}

    # 흐름 제어
    retry_count: int
    max_retries: int
    next_agent:  Literal["analyzer", "critic", "end"]
