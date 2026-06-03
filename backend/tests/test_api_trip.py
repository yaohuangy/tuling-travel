from pathlib import Path
import sys

from fastapi.testclient import TestClient


# 允许测试文件直接导入 backend/app 下的模块。
CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.main import app  # noqa: E402
import app.api.routes.export as export_route  # noqa: E402
import app.services.trip_service as trip_service  # noqa: E402

client = TestClient(app)


def build_generate_payload() -> dict:
    """构造一个合法的生成行程请求体。"""
    return {
        "destination": "大理",
        "start_date": "2026-04-10",
        "end_date": "2026-04-12",
        "travelers": 2,
        "budget": 3200,
        "preferences": ["自然风景", "拍照", "美食"],
        "pace": "轻松",
        "dietary_preferences": ["少辣"],
        "hotel_level": "舒适型",
        "special_notes": "不想太早起床，希望安排一个适合看日落的地点",
    }


def test_generate_trip_returns_itinerary_successfully() -> None:
    """测试 POST /trip/generate 能返回结构化 itinerary。"""
    response = client.post("/trip/generate", json=build_generate_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["destination"] == "大理"
    assert "trip_id" in data
    assert "summary" in data
    assert "days" in data
    assert isinstance(data["days"], list)
    assert len(data["days"]) == 3
    assert "budget_breakdown" in data
    assert data["budget_breakdown"]["total"] >= 0


def test_generate_trip_rejects_invalid_request() -> None:
    """测试非法请求会被 FastAPI/Pydantic 拦下。"""
    payload = build_generate_payload()
    payload["travelers"] = 0

    response = client.post("/trip/generate", json=payload)

    assert response.status_code == 422


def test_root_endpoint_returns_running_message() -> None:
    """测试根路径 / 能返回服务启动提示。"""
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Trip Planner Demo backend is running."}


def test_health_endpoint_returns_ok_status() -> None:
    """测试 /health 能返回健康检查结果。"""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_edit_trip_returns_updated_itinerary_successfully(monkeypatch) -> None:
    """测试 POST /trip/edit 能返回已修改的 itinerary。"""
    monkeypatch.setattr(trip_service, "generate_day_edit_draft", lambda request, target_day: (None, {"prompt_tokens": 0, "completion_tokens": 0}))

    generated_response = client.post("/trip/generate", json=build_generate_payload())
    generated_itinerary = generated_response.json()

    edit_payload = {
        "trip_id": generated_itinerary["trip_id"],
        "current_itinerary": generated_itinerary,
        "user_instruction": "第二天改得更轻松一点",
        "edit_scope": "day_2",
        "preserve_constraints": ["保留预算结构"],
    }

    response = client.post("/trip/edit", json=edit_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["trip_id"] == generated_itinerary["trip_id"]
    assert data["days"][1]["theme"].endswith("（已调整为更轻松）")


def test_edit_trip_rejects_invalid_request() -> None:
    """测试非法编辑请求会被 FastAPI/Pydantic 拦下。"""
    response = client.post(
        "/trip/edit",
        json={
            "trip_id": "trip_demo",
            "user_instruction": "第二天轻松一点",
        },
    )

    assert response.status_code == 422


def test_save_trip_returns_trip_id_successfully() -> None:
    """测试 POST /trip/save 能返回保存成功结果。"""
    generated_response = client.post("/trip/generate", json=build_generate_payload())
    generated_itinerary = generated_response.json()

    response = client.post(
        "/trip/save",
        json={
            "trip_id": generated_itinerary["trip_id"],
            "itinerary": generated_itinerary,
            "user_id": "user_001",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["trip_id"] == generated_itinerary["trip_id"]
    assert data["message"] == "Trip itinerary saved successfully."


def test_get_trip_detail_returns_saved_itinerary() -> None:
    """测试 GET /trip/{trip_id} 能返回已保存的 itinerary。"""
    generated_response = client.post("/trip/generate", json=build_generate_payload())
    generated_itinerary = generated_response.json()

    client.post(
        "/trip/save",
        json={
            "trip_id": generated_itinerary["trip_id"],
            "itinerary": generated_itinerary,
            "user_id": "user_001",
        },
    )

    response = client.get(f"/trip/{generated_itinerary['trip_id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["trip_id"] == generated_itinerary["trip_id"]
    assert data["itinerary"]["destination"] == "大理"


def test_get_trip_detail_returns_404_for_missing_trip() -> None:
    """测试查询不存在的 trip_id 时会返回 404。"""
    response = client.get("/trip/trip_not_exists")

    assert response.status_code == 404


def test_list_trips_returns_saved_trip_summaries() -> None:
    """测试 GET /trip 能返回已保存行程的摘要列表。"""
    generated_response = client.post("/trip/generate", json=build_generate_payload())
    generated_itinerary = generated_response.json()

    client.post(
        "/trip/save",
        json={
            "trip_id": generated_itinerary["trip_id"],
            "itinerary": generated_itinerary,
            "user_id": "user_001",
        },
    )

    response = client.get("/trip")

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)
    assert any(item["trip_id"] == generated_itinerary["trip_id"] for item in data["items"])


def test_export_trip_markdown_returns_markdown_text() -> None:
    """测试 GET /export/{trip_id}/markdown 可以导出 Markdown 文本。"""
    generated_response = client.post("/trip/generate", json=build_generate_payload())
    generated_itinerary = generated_response.json()

    client.post(
        "/trip/save",
        json={
            "trip_id": generated_itinerary["trip_id"],
            "itinerary": generated_itinerary,
            "user_id": "user_001",
        },
    )

    response = client.get(f"/export/{generated_itinerary['trip_id']}/markdown")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert generated_itinerary["destination"] in response.text
    assert generated_itinerary["summary"] in response.text


def test_export_trip_pdf_returns_pdf_bytes(monkeypatch) -> None:
    """测试 GET /export/{trip_id}/pdf 可以导出 PDF。"""
    generated_response = client.post("/trip/generate", json=build_generate_payload())
    generated_itinerary = generated_response.json()

    client.post(
        "/trip/save",
        json={
            "trip_id": generated_itinerary["trip_id"],
            "itinerary": generated_itinerary,
            "user_id": "user_001",
        },
    )

    monkeypatch.setattr(
        export_route,
        "itinerary_to_pdf_bytes",
        lambda trip_detail: b"%PDF-1.4\n%mock pdf\n",
    )

    response = client.get(f"/export/{generated_itinerary['trip_id']}/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF")


def test_generate_trip_response_includes_rag_context() -> None:
    """测试生成接口返回结果里包含最小 RAG 痕迹。"""
    response = client.post("/trip/generate", json=build_generate_payload())

    assert response.status_code == 200
    data = response.json()
    joined_notes = "\n".join(data["source_notes"])

    assert len(data["source_notes"]) >= 2
    assert "大理" in joined_notes
