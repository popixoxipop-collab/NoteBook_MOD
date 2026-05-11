from state import ReviewState


def route_next(state: ReviewState) -> str:
    return state.get("next_agent", "end")
