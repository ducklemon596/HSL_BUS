import json
import os
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery
from redis import Redis, RedisError

app = FastAPI(
    title="Bus HSL Fullstack API",
    description="Live Redis bus positions and historical BigQuery traffic analytics.",
)

# Environment configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "") or None
REDIS_PATTERN = os.getenv("REDIS_KEY_PATTERN", "bus:*")

PROJECT_ID = os.getenv("PROJECT_ID", "hsl-bus-streaming-495014")
DATASET_ID = os.getenv("DATASET_ID", "bus_analytics")
BIGQUERY_TABLE = f"{PROJECT_ID}.{DATASET_ID}.silver_bus_data"
DEFAULT_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"

# CORS configuration for browser-based frontend
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", DEFAULT_ALLOWED_ORIGINS).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Redis and BigQuery clients
redis_client = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
)

bq_client = bigquery.Client(project=PROJECT_ID)


def _normalize_trajectory(raw_trajectory: Any) -> List[Dict[str, float]]:
    if raw_trajectory is None:
        return []

    if isinstance(raw_trajectory, str):
        try:
            raw_trajectory = json.loads(raw_trajectory)
        except json.JSONDecodeError:
            return []

    if not isinstance(raw_trajectory, list):
        return []

    normalized = []
    for item in raw_trajectory:
        if isinstance(item, dict):
            lat = item.get("lat") or item.get("latitude") or item.get("y")
            lon = (
                item.get("lon")
                or item.get("lng")
                or item.get("longitude")
                or item.get("x")
            )
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            lat, lon = item[0], item[1]
        else:
            continue

        try:
            normalized.append({"lat": float(lat), "lon": float(lon)})
        except (TypeError, ValueError):
            continue

    return normalized


def _query_bigquery(
    sql: str, params: List[bigquery.ScalarQueryParameter]
) -> List[Dict[str, Any]]:
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    query_job = bq_client.query(sql, job_config=job_config)
    return [dict(row) for row in query_job.result()]


def _parse_json_object(raw_data: Optional[str]) -> Dict[str, Any]:
    if not raw_data:
        return {}

    try:
        parsed = json.loads(raw_data)
    except json.JSONDecodeError:
        return {}

    return parsed if isinstance(parsed, dict) else {}


def _clean_bus_id(redis_key: str) -> str:
    return redis_key.split("bus:", 1)[-1] if redis_key.startswith("bus:") else redis_key


def _effective_page_size(limit: int, offset: int) -> int:
    # Bus HSL convention: offset is used as the page-size control for historical views.
    return max(1, min(offset or limit, limit, 1000))


@app.get("/api/buses/live")
def get_live_buses() -> Dict[str, Any]:
    try:
        keys = list(redis_client.scan_iter(match=REDIS_PATTERN, count=500))
    except RedisError as exc:
        raise HTTPException(status_code=502, detail=f"Redis scan failed: {exc}")

    if not keys:
        return {"buses": []}

    try:
        pipe = redis_client.pipeline()
        for key in keys:
            pipe.hmget(key, ["data", "window_avg_speed", "is_stuck", "window_end_time"])
        redis_rows = pipe.execute()
    except RedisError as exc:
        raise HTTPException(status_code=502, detail=f"Redis pipeline failed: {exc}")

    buses = []
    for key, hash_values in zip(keys, redis_rows):
        raw_data, avg_speed, is_stuck, window_end_time = hash_values
        data = _parse_json_object(raw_data)
        if not data:
            continue

        if avg_speed is not None:
            data["avg_speed"] = avg_speed
        if is_stuck is not None:
            data["is_stuck"] = str(is_stuck).lower() == "true"
        if window_end_time is not None:
            data["window_end_time"] = window_end_time

        buses.append({"id": _clean_bus_id(str(key)), "data": data})

    return {"buses": buses}


@app.get("/api/routes/impact")
def get_route_impact(
    start_date: date = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: date = Query(..., description="End date in YYYY-MM-DD format"),
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(10, ge=1, le=1000, description="Bus HSL page-size control"),
) -> Dict[str, Any]:
    if start_date > end_date:
        raise HTTPException(
            status_code=400, detail="start_date must be on or before end_date"
        )

    page_size = _effective_page_size(limit, offset)
    sql = f"""
        SELECT
          desi AS route_id,
          SUM(observed_duration_seconds) / 3600.0 AS total_stuck_hours,
          COUNT(DISTINCT unique_veh_id) AS affected_bus_count
        FROM `{BIGQUERY_TABLE}`
        WHERE traffic_status IN ('HEAVY', 'GRIDLOCK')
          AND event_date BETWEEN @start_date AND @end_date
        GROUP BY route_id
        ORDER BY total_stuck_hours DESC
        LIMIT @page_size
    """
    params = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        bigquery.ScalarQueryParameter("page_size", "INT64", page_size),
    ]

    try:
        rows = _query_bigquery(sql, params)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"BigQuery request failed: {exc}")

    return {"routes": rows, "limit": limit, "offset": offset, "page_size": page_size}


@app.get("/api/traffic/ratio")
def get_traffic_ratio(
    start_date: date = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: date = Query(..., description="End date in YYYY-MM-DD format"),
) -> Dict[str, Any]:
    if start_date > end_date:
        raise HTTPException(
            status_code=400, detail="start_date must be on or before end_date"
        )

    sql = f"""
        WITH status_durations AS (
          SELECT
            traffic_status,
            SUM(observed_duration_seconds) AS duration_seconds
          FROM `{BIGQUERY_TABLE}`
          WHERE event_date BETWEEN @start_date AND @end_date
          GROUP BY traffic_status
        ),
        with_total AS (
          SELECT
            traffic_status,
            duration_seconds,
            SUM(duration_seconds) OVER () AS total_duration_seconds
          FROM status_durations
        )
        SELECT
          traffic_status,
          duration_seconds,
          SAFE_DIVIDE(duration_seconds, total_duration_seconds) * 100 AS ratio_percent
        FROM with_total
        ORDER BY ratio_percent DESC
    """
    params = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
    ]

    try:
        rows = _query_bigquery(sql, params)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"BigQuery request failed: {exc}")

    return {"stats": rows}


@app.get("/api/traffic/stats")
def get_traffic_stats(
    start_date: date = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: date = Query(..., description="End date in YYYY-MM-DD format"),
) -> Dict[str, Any]:
    return get_traffic_ratio(start_date=start_date, end_date=end_date)


@app.get("/api/traffic/heatmap")
def get_traffic_heatmap(
    start_date: date = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: date = Query(..., description="End date in YYYY-MM-DD format"),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(500, ge=1, le=5000, description="Bus HSL page-size control"),
    min_intensity: int = Query(1, ge=1),
) -> Dict[str, Any]:
    if start_date > end_date:
        raise HTTPException(
            status_code=400, detail="start_date must be on or before end_date"
        )

    page_size = _effective_page_size(limit, offset)
    sql = f"""
        SELECT
          ROUND(SAFE_CAST(point.lat AS FLOAT64), 3) AS grid_lat,
          ROUND(SAFE_CAST(point.long AS FLOAT64), 3) AS grid_lon,
          COUNT(*) AS intensity
        FROM `{BIGQUERY_TABLE}`,
        UNNEST(IFNULL(trajectory, [])) AS point
        WHERE traffic_status IN ('HEAVY', 'GRIDLOCK')
          AND event_date BETWEEN @start_date AND @end_date
        GROUP BY grid_lat, grid_lon
        HAVING intensity > @min_intensity
        ORDER BY intensity DESC
        LIMIT @page_size
    """
    params = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        bigquery.ScalarQueryParameter("min_intensity", "INT64", min_intensity),
        bigquery.ScalarQueryParameter("page_size", "INT64", page_size),
    ]

    try:
        rows = _query_bigquery(sql, params)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"BigQuery request failed: {exc}")

    return {"points": rows, "limit": limit, "offset": offset, "page_size": page_size}


@app.get("/api/traffic/jam")
def get_traffic_jam(
    start_date: date = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: date = Query(..., description="End date in YYYY-MM-DD format"),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(500, ge=1, le=5000, description="Bus HSL page-size control"),
    min_intensity: int = Query(1, ge=1),
) -> Dict[str, Any]:
    heatmap = get_traffic_heatmap(
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
        min_intensity=min_intensity,
    )
    return {"results": heatmap["points"], **heatmap}
