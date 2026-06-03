from pathlib import Path
import sys


# 允许测试文件直接导入 backend/app 下的模块。
CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models.schemas import TripEditRequest, TripRequest  # noqa: E402
from app.services.trip_service import edit_trip_itinerary, generate_trip_itinerary  # noqa: E402
import app.services.trip_service as trip_service  # noqa: E402


'''
给一个 TripRequest，service 会不会正确返回 Itinerary。

测试内容：
    能接收 TripRequest
    能返回结构正确的 Itinerary
    能根据日期和偏好生成合理的演示结果
'''
def build_trip_request() -> TripRequest:
    """构造一个合法的 TripRequest，供 service 测试复用。"""
    return TripRequest(
        destination="大理",
        start_date="2026-04-10",
        end_date="2026-04-12",
        travelers=2,
        budget=3200,
        preferences=["自然风景", "拍照", "美食"],
        pace="轻松",
        dietary_preferences=["少辣"],
        hotel_level="舒适型",
        special_notes="不想太早起床，希望安排一个适合看日落的地点",
    )


def test_generate_trip_itinerary_returns_itinerary_object() -> None:
    """测试 service 能返回一个结构完整的 itinerary。"""
    request = build_trip_request()

    itinerary = generate_trip_itinerary(request)

    assert itinerary.destination == "大理"
    assert itinerary.trip_id.startswith("trip_")
    assert itinerary.summary != ""
    assert len(itinerary.days) == 3
    assert itinerary.budget_breakdown.total >= 0


def test_generate_trip_itinerary_builds_day_plans_by_date_range() -> None:
    """测试 service 会根据日期范围生成对应天数的 DayPlan。"""
    request = build_trip_request()

    itinerary = generate_trip_itinerary(request)

    assert len(itinerary.days) == 3
    assert itinerary.days[0].day_index == 1
    assert itinerary.days[1].day_index == 2
    assert itinerary.days[2].day_index == 3


def test_generate_trip_itinerary_keeps_request_preferences_in_summary() -> None:
    """测试用户偏好会被写入返回摘要中。"""
    request = build_trip_request()

    itinerary = generate_trip_itinerary(request)

    assert "自然风景" in itinerary.summary
    assert "拍照" in itinerary.summary
    assert "美食" in itinerary.summary

'''
测的是：
    service 能不能基于旧 Itinerary 做修改
    edit_scope="day_2" 是否真的改到第二天
    用户指令是否真的影响结果
'''
def test_edit_trip_itinerary_updates_target_day_theme(monkeypatch) -> None:
    """测试编辑逻辑可以修改指定天数的主题与备注。"""
    monkeypatch.setattr(trip_service, "generate_day_edit_draft", lambda request, target_day: (None, {"prompt_tokens": 0, "completion_tokens": 0}))
    original_itinerary = generate_trip_itinerary(build_trip_request())

    edit_request = TripEditRequest(
        trip_id=original_itinerary.trip_id,
        current_itinerary=original_itinerary,
        user_instruction="第二天改得更轻松一点",
        edit_scope="day_2",
        preserve_constraints=["保留预算结构"],
    )

    updated_itinerary = edit_trip_itinerary(edit_request)

    assert updated_itinerary.days[1].theme.endswith("（已调整为更轻松）")
    assert "已根据用户要求把节奏调整得更轻松。" in updated_itinerary.days[1].notes


def test_edit_trip_itinerary_can_replace_first_spot_with_free_time(monkeypatch) -> None:
    “””测试”不要安排”指令会把景点调整成自由活动。”””
    monkeypatch.setattr(trip_service, “generate_day_edit_draft”, lambda request, target_day: (None, {“prompt_tokens”: 0, “completion_tokens”: 0}))
    original_itinerary = generate_trip_itinerary(build_trip_request())

    edit_request = TripEditRequest(
        trip_id=original_itinerary.trip_id,
        current_itinerary=original_itinerary,
        user_instruction="第二天不要安排景点了",
        edit_scope="day_2",
        preserve_constraints=[],
    )

    updated_itinerary = edit_trip_itinerary(edit_request)

    assert updated_itinerary.days[1].spots[0].name == "自由活动 / 弹性安排"
    assert "减少固定景点安排" in updated_itinerary.days[1].spots[0].description


def test_edit_trip_itinerary_can_apply_llm_day_edit(monkeypatch) -> None:
    """测试当 LLM 编辑草稿可用时，会优先重写目标日安排。"""

    class FakeDayEditDraft:
        theme = "更轻松的洱海慢游"
        spot_name = "双廊古镇"
        spot_description = "更适合慢节奏看海和看日落。"
        meal_name = "海景下午茶"
        meal_notes = "少辣，轻松休息。"
        daily_note = "下午再出发，去双廊慢慢看日落。"

    monkeypatch.setattr(
        trip_service,
        "generate_day_edit_draft",
        lambda request, target_day: (FakeDayEditDraft(), {"prompt_tokens": 80, "completion_tokens": 30}),
    )
    original_itinerary = generate_trip_itinerary(build_trip_request())

    edit_request = TripEditRequest(
        trip_id=original_itinerary.trip_id,
        current_itinerary=original_itinerary,
        user_instruction="第二天改得更轻松一点，不要安排太满",
        edit_scope="day_2",
        preserve_constraints=["保留预算结构"],
    )

    updated_itinerary = edit_trip_itinerary(edit_request)

    assert updated_itinerary.days[1].theme == "更轻松的洱海慢游"
    assert updated_itinerary.days[1].spots[0].name == "双廊古镇"
    assert updated_itinerary.days[1].meals[0].name == "海景下午茶"
    assert updated_itinerary.days[1].notes[-1] == "下午再出发，去双廊慢慢看日落。"

def test_generate_trip_itinerary_includes_local_guide_context() -> None:
    """测试生成结果已经开始包含本地攻略检索信息。"""
    itinerary = generate_trip_itinerary(build_trip_request())

    joined_notes = "\n".join(itinerary.source_notes)
    joined_spots = "\n".join(day.spots[0].name for day in itinerary.days if day.spots)

    assert len(itinerary.source_notes) >= 2
    assert "大理" in joined_notes
    assert (
        "大理古城" in joined_spots
        or "喜洲古镇" in joined_spots
        or "崇圣寺三塔" in joined_spots
        or "洱海生态廊道" in joined_spots
    )
