"""
노트북에 모듈화 메타데이터를 주입하는 테스트 스크립트.
실제 서비스에서는 백엔드가 이 메타데이터를 자동으로 생성하고
노트북에 삽입한다.

실행: python test_metadata_injection.py
"""
import json
import copy

NOTEBOOK_PATH = "/Users/xox/Downloads/Step1_상품리뷰분석_Agent_1_완성.ipynb"
OUTPUT_PATH   = "/Users/xox/Desktop/NoteBook_MOD/extension/test_output_with_meta.ipynb"

# 서비스가 자동 생성하는 모듈 정보 (백엔드 분석 결과 예시)
MOCK_MODULES = {
    # 셀 인덱스 → 해당 셀의 모듈 목록
    28: [  # ReviewState 셀
        {
            "funcName": "ReviewState",
            "filePath": "state.py",
            "sourceCode": (
                "from typing import TypedDict, Optional, Dict, Any, Literal\n\n"
                "class ReviewState(TypedDict):\n"
                "    review:          str\n"
                "    analyzer_result: Optional[Dict[str, Any]]\n"
                "    critic_result:   Optional[Dict[str, Any]]\n"
                "    retry_count:     int\n"
                "    max_retries:     int\n"
                "    next_agent:      Literal['analyzer', 'critic', 'end']\n"
            ),
        }
    ],
    33: [  # analyzer_node 셀
        {
            "funcName": "analyzer_node",
            "filePath": "agents/analyzer_node.py",
            "sourceCode": (
                "def analyzer_node(state: ReviewState):\n"
                "    review = state['review']\n"
                "    # ... ABSA 분석 로직\n"
                "    response = llm.invoke(messages)\n"
                "    return {'analyzer_result': result}\n"
            ),
        }
    ],
    35: [  # critic_node 셀
        {
            "funcName": "critic_node",
            "filePath": "agents/critic_node.py",
            "sourceCode": (
                "def critic_node(state: ReviewState):\n"
                "    review          = state['review']\n"
                "    analyzer_result = state.get('analyzer_result', {})\n"
                "    # ... 검증 로직\n"
                "    return {'critic_result': result}\n"
            ),
        }
    ],
    37: [  # supervisor_node 셀
        {
            "funcName": "supervisor_node",
            "filePath": "agents/supervisor_node.py",
            "sourceCode": (
                "def supervisor_node(state: ReviewState):\n"
                "    # 흐름 제어 로직\n"
                "    if analyzer_result is None:\n"
                "        return {'next_agent': 'analyzer'}\n"
                "    if verdict == 'Conformity':\n"
                "        return {'next_agent': 'end'}\n"
                "    return {'next_agent': 'analyzer', 'retry_count': retry_count + 1}\n"
            ),
        }
    ],
    40: [  # route_next 셀
        {
            "funcName": "route_next",
            "filePath": "graph/route_next.py",
            "sourceCode": (
                "def route_next(state: ReviewState) -> str:\n"
                "    return state.get('next_agent', 'end')\n"
            ),
        }
    ],
}


def inject_metadata(notebook_path: str, output_path: str) -> None:
    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    nb_out = copy.deepcopy(nb)

    for cell_idx, modules in MOCK_MODULES.items():
        cell = nb_out["cells"][cell_idx]
        if cell["cell_type"] != "code":
            continue

        # JupyterLab 셀 메타데이터에 notebook_mod 키 삽입
        cell.setdefault("metadata", {})["notebook_mod"] = {
            "enabled": True,
            "modules": modules,
        }
        print(f"  ✓ 셀 [{cell_idx}] 메타데이터 주입: {[m['funcName'] for m in modules]}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(nb_out, f, ensure_ascii=False, indent=1)

    print(f"\n저장 완료: {output_path}")
    print("JupyterLab에서 열면 뱃지 UI가 적용됩니다.")


if __name__ == "__main__":
    inject_metadata(NOTEBOOK_PATH, OUTPUT_PATH)
