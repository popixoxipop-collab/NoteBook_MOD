import json
import re
from langchain_core.messages import SystemMessage, HumanMessage
from state import ReviewState


def critic_node(state: ReviewState):
    from graph.builder import llm

    review          = state["review"]
    analyzer_result = state.get("analyzer_result", {})

    system_prompt = """당신은 화장품 리뷰 분석 결과를 검증하는 전문가입니다.

검증 기준:
- OUTPUT_ERROR: JSON 파싱 불가, items가 list가 아님, aspect/label/evidence 누락, label이 0 또는 1이 아님
- SCOPE_ERROR: aspect가 {보습, 가격, 향, 포장} 외의 값 사용
- EVIDENCE_ERROR: evidence가 리뷰 원문에 없거나 요약·변형된 형태
- QUALITY_ERROR: 환각, 감성 판단 모호, 반복해도 개선 어려운 근본적 오류

모든 기준 통과 시 Conformity(적합), 위반 시 Non-conformity(부적합).

출력 형식 (코드블록 없이 JSON 1개):
{"verdict": "Conformity" 또는 "Non-conformity", "reason": "판단 이유", "reason_code": null 또는 "OUTPUT_ERROR|SCOPE_ERROR|EVIDENCE_ERROR|QUALITY_ERROR", "repair_directive": null 또는 "수정 지시"}"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"리뷰 원문: {review}\n\n분석 결과: {json.dumps(analyzer_result, ensure_ascii=False)}")
    ]

    response = llm.invoke(messages)
    content  = response.content.strip()

    try:
        content_clean = re.sub(r'```(?:json)?\s*', '', content)
        content_clean = re.sub(r'```\s*', '', content_clean).strip()
        result = json.loads(content_clean)
    except json.JSONDecodeError:
        result = {
            "verdict": "Non-conformity",
            "reason": "critic 출력 파싱 실패",
            "reason_code": "OUTPUT_ERROR",
            "repair_directive": "코드블록 없이 JSON 1개만 출력하세요."
        }

    return {"critic_result": result}
