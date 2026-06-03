# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

途灵 (Tuling) is an AI-powered travel planning system that integrates LLM generation, RAG-enhanced local guides, Amap (高德地图) map services, and weather data. Users input destination, dates, budget, traveler count, and preferences; the system outputs a structured itinerary with map points, weather, budget breakdown, and exportable documents.

## Tech Stack

- **Backend**: FastAPI + Pydantic + SQLAlchemy + LangChain + DashScope (`qwen-max`)
- **Vector DB**: ChromaDB (persistent, cosine similarity)
- **Cache**: Redis (optional, with graceful degradation)
- **External**: Amap Web Services (geocoding, POI, routing, weather) via HTTPX
- **Frontend**: Vue 3 + Vite + Ant Design Vue + TypeScript
- **Database**: SQLite (via SQLAlchemy)

## Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env   # then fill in API keys
uvicorn app.api.main:app --host 0.0.0.0 --port 8000

# RAG data initialization (one-time, before first use)
cd backend
python scripts/ingest_data.py

# Frontend
cd frontend
npm install
cp .env.example .env   # then fill VITE_API_BASE_URL and VITE_AMAP_JS_KEY
npm run dev             # starts on :5173

# Tests
cd backend
pytest tests/test_api_trip.py -q
pytest tests/test_models_schemas.py -q
pytest tests/test_rag_retriever.py -q
pytest tests/test_services_trip.py -q
pytest tests/test_storage_service.py -q
pytest tests/test_trip_planner_agent.py -q
```

## Core Architecture: Explicit Orchestration

The system uses **explicit orchestration** (not agentic autonomous decision-making). The central orchestrator is `backend/app/services/trip_service.py`, which calls each step in a fixed sequence:

```
POST /trip/generate
  → trip.py (route)
    → trip_service.py (orchestrator)
      ① RAG retrieval (rag_tool.py → retriever.py → vector_db.py)
      ② LLM itinerary generation (trip_planner_agent.py → qwen-max)
      ③ Map enrichment per spot (map_service.py → Amap APIs)
      ④ Weather query (weather_service.py → Amap APIs)
      ⑤ Budget breakdown calculation
      ⑥ Token usage aggregation
      → return Itinerary
```

The edit flow (`POST /trip/edit`) follows the same pattern but targets a single day and re-enriches map data after editing.

## Pervasive Fallback Pattern

Nearly every critical component has a **multi-tier fallback chain**, always degrading gracefully rather than failing:

| Component | Tier 1 | Tier 2 | Tier 3 |
|-----------|--------|--------|--------|
| Query Rewrite | LLM-based (qwen-max) | Rule-based keyword extraction | — |
| Embedding | Direct DashScope API call (for official token counts) | LangChain OpenAIEmbeddings (no token count) | Keyword-based text matching (no embeddings at all) |
| Vector Search | ChromaDB cosine similarity | Keyword-based text matching | — |
| Rerank | Cross-encoder (qwen3-rerank via DashScope) | Rule-based scoring | — |
| LLM Generation | qwen-max via LangChain | Rule-based fallback itinerary | — |
| Redis Cache | Redis hit | Cache miss → compute → write back | Redis unavailable → skip entirely |
| Map Enrichment | Configured on (`ENABLE_AMAP_ENRICHMENT=true`) | Configured off → skip | Exception during enrichment → silently skip that item |

Each component returns `empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}` on failure so the token tracking pipeline stays consistent.

## RAG Pipeline (Online Phase)

The retrieval chain has its own multi-stage pipeline with caching at two levels:

```
User input
  → ① Query Rewrite (LLM → rule fallback)
  → ② Embedding (API → LangChain fallback)
  → ③ RAG cache check (Redis key: rag:guide:{query}:{top_k})
  → ④ ChromaDB vector recall (top candidate_k = top_k * 2, min 6)
  → ⑤ Noise pre-filtering (drops "文档开头" fragments)
  → ⑥ Rerank cache check (Redis key: rerank:{query}:{chunk_hash})
  → ⑦ Cross-encoder Rerank (qwen3-rerank → rule fallback)
  → ⑧ Write rerank results to cache
  → ⑨ Return top-k text fragments to LLM prompt
```

RAG and rerank results each have their own Redis cache with independent TTLs. Rerank cache keys are built from `query + hash(chunk source:title list)` so cache invalidates when either query or candidate chunks change.

## Cache Architecture

`backend/app/services/cache_service.py` provides a **lazy-loaded, gracefully-degrading Redis wrapper**:

- Client is created on first access (`_get_redis_client()`), not at import time
- If `REDIS_ENABLED=false` or Redis is unreachable, all `get_cached_json`/`set_cached_json` calls silently return `None`/skip — no exceptions propagate to callers
- All keys are prefixed with `REDIS_KEY_PREFIX` (default `trip_planner`) to avoid cross-project collisions
- Individual TTLs per domain: weather (30min), map (24h), RAG (6h), rerank (6h), default (30min)
- JSON serialization via `json.dumps(value, ensure_ascii=False)` for Chinese content

## Token Usage Tracking

Token consumption is tracked per pipeline stage through dedicated models in `schemas.py`:

- `TokenUsage` records prompt/completion tokens for: Query Rewrite, Query Embedding, Rerank, Planner (LLM generation)
- Each stage returns its own `dict[str, int]` usage; `trip_service.py` aggregates them into one `TokenUsage` object
- Token data flows through the API response (`/trip/generate` returns `token_usage` field)
- `/trip/stats` aggregates across all saved trips
- Backend prints per-stage token counts to stdout for monitoring

Token extraction is done from raw API responses when possible (`response_metadata.token_usage` for LangChain, `usage` field for DashScope APIs). Fallback: `{prompt_tokens: 0, completion_tokens: 0}` when unavailable.

## Data Model Separation

- **`backend/app/models/schemas.py`**: Pydantic models for API request/response validation and the core `Itinerary`/`DayPlan`/`SpotItem` domain models. These are the wire format.
- **`backend/app/models/db_models.py`**: SQLAlchemy ORM model (`TripRecord`) for SQLite persistence. Stores the entire itinerary as a JSON string in `itinerary_json` column, with indexed `trip_id` for lookups.

The two are bridged in `storage_service.py` via `json.dumps(itinerary.model_dump(mode="json"))` on save and `Itinerary(**json.loads(record.itinerary_json))` on read.

## Config Patterns

`backend/app/config.py`:
- Resolves `BACKEND_DIR` from its own file location (`Path(__file__).resolve().parent.parent`)
- Loads `.env` from `BACKEND_DIR/.env`
- Relative paths (e.g., `CHROMA_DB_DIR`) are resolved against `BACKEND_DIR`
- Creates directories on import (DB dir, Chroma dir) via `mkdir(parents=True, exist_ok=True)`
- SQLite uses `check_same_thread=False` for FastAPI's async context

## Frontend Architecture

Three SPA views managed in `App.vue`:
- `Home.vue` — trip planning form (collects user input, calls `/trip/generate`)
- `Result.vue` — displays generated itinerary with map (`AmapTripMap.vue`), weather, budget; supports save, edit, export
- `History.vue` — lists saved trips, supports view/open/delete

`frontend/src/services/api.ts` is the single Axios wrapper for all backend communication. `frontend/src/types/index.ts` mirrors the backend Pydantic schemas in TypeScript.

## Environment Variables

Backend requires `.env` in `backend/` with: `LLM_API_KEY` (DashScope), `AMAP_API_KEY` (Amap Web Service). Frontend requires `.env` in `frontend/` with: `VITE_API_BASE_URL`, `VITE_AMAP_JS_KEY` (Amap JavaScript API — different from the backend web service key). Redis is optional (`REDIS_ENABLED=false` by default).

## Key Scripts

- `backend/scripts/ingest_data.py` — one-time: chunks local Markdown guides, embeds with `text-embedding-v4`, writes to ChromaDB
- `backend/scripts/debug_rag_retrieval.py` — debug RAG pipeline: shows query, top-k chunks, rerank scores and reasons
- `backend/scripts/evaluate_rag_retrieval.py` — quantitative RAG eval against `backend/eval/rag_eval_cases.json`
- `backend/scripts/test_map_service.py` — standalone Amap service test
- `backend/scripts/test_trip_service_real.py` — end-to-end trip generation with real API calls
