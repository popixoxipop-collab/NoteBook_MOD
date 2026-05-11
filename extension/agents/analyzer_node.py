import json
import re
from langchain_core.messages import SystemMessage, HumanMessage
from state import ReviewState


def analyzer_node(state: ReviewState):
    from graph.builder import llm

    review = state["review"]

    system_prompt = """당신은 화장품 리뷰의 속성별 감성 분석(ABSA) 전문가입니다.
주어진 리뷰에서 언급된 속성과 해당 감성을 추출하세요.

분석 대상 속성: 보습, 가격, 향, 포장

출력 규칙:
- 코드블록 없이 JSON 1개만 출력
- items는 list, 각 item은 {aspect, label, evidence} 필수
- label은 0(부정) 또는 1(긍정)만 허용
- aspect는 {보습, 가격, 향, 포장} 중 하나만 사용
- evidence는 리뷰 원문에서 그대로 복사한 연속 문자열(substring)만 사용
- 리뷰에 언급되지 않은 속성은 포함하지 말 것

출력 형식:
{"items": [{"aspect": "속성명", "label": 0또는1, "evidence": "리뷰 원문 substring"}]}"""

    repair_directive = ""
    if state.get("critic_result") and state["critic_result"].get("repair_directive"):
        repair_directive = f"\n\n[수정 지시사항]: {state['critic_result']['repair_directive']}"

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"리뷰: {review}{repair_directive}")
    ]

    response = llm.invoke(messages)
    content  = response.content.strip()

    try:
        content_clean = re.sub(r'```(?:json)?\s*', '', content)
        content_clean = re.sub(r'```\s*', '', content_clean).strip()
        result = json.loads(content_clean)
    except json.JSONDecodeError:
        result = {"items": [], "parse_error": content}

    return {"analyzer_result": result}
