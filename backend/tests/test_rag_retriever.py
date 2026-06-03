from pathlib import Path
import sys


# 允许测试文件直接导入 backend/app 下的模块。
CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.rag.retriever as retriever  # noqa: E402


def test_retrieve_travel_guide_formats_chunks_as_text(monkeypatch) -> None:
    """测试 retriever 会把检索结果格式化成可直接引用的文本片段。"""

    def fake_search_guide_chunks_with_usage(
        query: str, top_k: int = 3
    ) -> tuple[list[dict[str, str]], dict[str, int]]:
        assert query == "大理 古城 美食"
        assert top_k == 6
        return [
            {
                "source": "dali_guide.md",
                "title": "大理古城",
                "text": "大理古城适合慢游和拍照。",
            }
        ], {"prompt_tokens": 0, "completion_tokens": 0}

    monkeypatch.setattr(retriever, "search_guide_chunks_with_usage", fake_search_guide_chunks_with_usage)
    monkeypatch.setattr(
        retriever,
        "rerank_guide_chunks",
        lambda query, matched_chunks, top_k, destination=None: (
            matched_chunks[:top_k],
            {"prompt_tokens": 0, "completion_tokens": 0},
        ),
    )

    results, _, _ = retriever.retrieve_travel_guide("大理 古城 美食", top_k=2)

    assert results == ["[来源: dali_guide.md | 标题: 大理古城]\n大理古城适合慢游和拍照。"]


def test_retrieve_travel_guide_returns_empty_when_no_chunks(monkeypatch) -> None:
    """测试没有召回任何片段时，会返回空列表。"""

    def fake_search_guide_chunks_with_usage(
        query: str, top_k: int = 3
    ) -> tuple[list[dict[str, str]], dict[str, int]]:
        assert query == "火星 沙漠 极地科考"
        assert top_k == 6
        return [], {"prompt_tokens": 0, "completion_tokens": 0}

    monkeypatch.setattr(retriever, "search_guide_chunks_with_usage", fake_search_guide_chunks_with_usage)
    monkeypatch.setattr(
        retriever,
        "rerank_guide_chunks",
        lambda query, matched_chunks, top_k, destination=None: (
            matched_chunks[:top_k],
            {"prompt_tokens": 0, "completion_tokens": 0},
        ),
    )

    results, _, _ = retriever.retrieve_travel_guide("火星 沙漠 极地科考", top_k=2)

    assert results == []
