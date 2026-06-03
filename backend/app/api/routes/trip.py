from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    Itinerary,
    TokenStatsResponse,
    TripDetailResponse,
    TripEditRequest,
    TripListResponse,
    TripRequest,
    TripSaveRequest,
)
from app.services.storage_service import (
    delete_itinerary_by_trip_id,
    get_itinerary_by_trip_id,
    get_token_stats,
    list_saved_itineraries,
    save_itinerary,
)
from app.services.trip_service import edit_trip_itinerary, generate_trip_itinerary


router = APIRouter(prefix="/trip", tags=["trip"])


@router.get("", response_model=TripListResponse)
def list_trips() -> TripListResponse:
    """返回已保存行程的摘要列表。"""
    return list_saved_itineraries()


@router.post("/generate", response_model=Itinerary)
def generate_trip(request: TripRequest) -> Itinerary:
    """生成结构化 itinerary。"""
    return generate_trip_itinerary(request)


@router.get("/stats", response_model=TokenStatsResponse)
def get_trip_token_stats() -> TokenStatsResponse:
    """返回所有已保存行程的 token 消耗统计。"""
    return get_token_stats()


@router.post("/edit", response_model=Itinerary)
def edit_trip(request: TripEditRequest) -> Itinerary:
    """根据用户编辑指令返回更新后的 itinerary。"""
    return edit_trip_itinerary(request)


@router.post("/save")
def save_trip(request: TripSaveRequest) -> dict[str, str]:
    """保存 itinerary，并返回 trip_id。"""
    saved_trip_id = save_itinerary(request.itinerary)
    return {
        "message": "Trip itinerary saved successfully.",
        "trip_id": saved_trip_id,
    }


@router.get("/{trip_id}", response_model=TripDetailResponse)
def get_trip_detail(trip_id: str) -> TripDetailResponse:
    """根据 trip_id 查询已保存 itinerary。"""
    trip_detail = get_itinerary_by_trip_id(trip_id)
    if trip_detail is None:
        raise HTTPException(status_code=404, detail="Trip not found.")
    return trip_detail


@router.delete("/{trip_id}")
def delete_trip(trip_id: str) -> dict[str, str]:
    """根据 trip_id 删除已保存 itinerary。"""
    deleted = delete_itinerary_by_trip_id(trip_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Trip not found.")
    return {
        "message": "Trip itinerary deleted successfully.",
        "trip_id": trip_id,
    }
