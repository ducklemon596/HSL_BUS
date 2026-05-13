import json
import os
from datetime import date
from typing import Any, Dict, List

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

# CORS configuration for browser-based frontend
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
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


@app.get("/api/buses/live")
def get_live_buses() -> Dict[str, Any]:
    try:
        keys = list(redis_client.scan_iter(match=REDIS_PATTERN, count=500))
    except RedisError as exc:
        raise HTTPException(status_code=502, detail=f"Redis scan failed: {exc}")

    buses = []
    for key in keys:
        try:
            raw_data = redis_client.hget(key, "data")
        except RedisError:
            continue

        if not raw_data:
            continue

        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            continue

        buses.append(
            {
                "id": key,
                "data": data,
            }
        )

    return {"buses": buses}


@app.get("/api/traffic/jam")
def get_traffic_jam(
    start_date: date = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: date = Query(..., description="End date in YYYY-MM-DD format"),
) -> Dict[str, Any]:
    if start_date > end_date:
        raise HTTPException(
            status_code=400, detail="start_date must be on or before end_date"
        )

    sql = f"""
        SELECT unique_veh_id, traffic_status, trajectory, event_date
        FROM `{BIGQUERY_TABLE}`
        WHERE traffic_status IN ('GRIDLOCK', 'LIGHT', 'HEAVY')
          AND event_date BETWEEN @start_date AND @end_date
        ORDER BY event_date DESC
        LIMIT 500
    """
    params = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
    ]

    try:
        rows = _query_bigquery(sql, params)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"BigQuery request failed: {exc}")

    for row in rows:
        row["trajectory"] = _normalize_trajectory(row.get("trajectory"))

    return {"results": rows}


@app.get("/api/traffic/stats")
def get_traffic_stats(
    start_date: date = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: date = Query(..., description="End date in YYYY-MM-DD format"),
) -> Dict[str, Any]:
    if start_date > end_date:
        raise HTTPException(
            status_code=400, detail="start_date must be on or before end_date"
        )

    sql = f"""
        SELECT traffic_status, COUNT(1) AS count
        FROM `{BIGQUERY_TABLE}`
        WHERE event_date BETWEEN @start_date AND @end_date
        GROUP BY traffic_status
        ORDER BY count DESC
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
