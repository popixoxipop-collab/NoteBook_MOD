from state import ReviewState


def supervisor_node(state: ReviewState):
    analyzer_result = state.get("analyzer_result")
    critic_result   = state.get("critic_result")
    retry_count     = state.get("retry_count", 0)
    max_retries     = state.get("max_retries", 2)

    # analyzer 미실행 → analyzer로
    if analyzer_result is None:
        return {"next_agent": "analyzer"}

    # critic 미실행 또는 재시도 후 pending 상태 → critic으로
    if critic_result is None or critic_result.get("verdict") == "pending":
        return {"next_agent": "critic"}

    verdict     = critic_result.get("verdict", "")
    reason_code = critic_result.get("reason_code", "")

    # 적합 → 종료
    if verdict == "Conformity":
        return {"next_agent": "end"}

    # QUALITY_ERROR 또는 최대 재시도 초과 → 종료
    if reason_code == "QUALITY_ERROR" or retry_count >= max_retries:
        return {"next_agent": "end"}

    # 재시도: repair_directive 보존, critic 결과 pending 처리
    repair_directive = critic_result.get("repair_directive")
    return {
        "next_agent":    "analyzer",
        "retry_count":   retry_count + 1,
        "critic_result": {"verdict": "pending", "repair_directive": repair_directive}
    }
