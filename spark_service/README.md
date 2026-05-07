# Spark Service - HSL Bus Pipeline

Spark streaming worker for processing real-time HSL bus data from Kafka, performing data validation and transformations, and writing to Redis and GCS storage layers.

## Overview

The Spark service reads vehicle position data from Kafka, cleans and validates it, and distributes the processed data across multiple destinations:
- **Redis** — Real-time position and speed averages for live UI updates
- **GCS Bronze Layer** — Raw unprocessed data for archival
- **GCS Silver Layer** — Cleaned and aggregated data in Delta Lake format

## Module Structure

### Core Modules

| Module | Purpose |
|--------|---------|
| `run_spark_worker.py` | Orchestration entrypoint; initializes Spark session and starts all streaming pipelines |
| `schemas.py` | Pyspark schema definitions for VP (Vehicle Position) and Bus data |
| `spark_session.py` | Spark session builder with Google Cloud Dataproc configuration |
| `kafka_reader.py` | Reads raw data from Kafka topics |
| `data_pipeline.py` | Data cleaning and validation (geographic bounds, speed, heading, occupancy) |
| `redis_writer.py` | Distributed Redis writes using Lua scripts for position and speed data |
| `storage_writer.py` | Bronze and Silver layer writers using Parquet and Delta Lake |

## Running the Service

### Prerequisites

1. **Environment Setup**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration**
   - Ensure `hsl_common` shared library is installed
   - Set environment variables via `.env` file (see `hsl_common/settings.py` for required keys)

3. **GCP & Infrastructure**
   - Google Cloud Storage buckets configured for Bronze/Silver paths
   - Redis cluster accessible at `REDIS_HOST:REDIS_PORT`
   - Kafka broker available at `SPARK_KAFKA_BOOTSTRAP_SERVERS`
   - Dataproc cluster (if running on GCP)

### Local Development

```bash
python run_spark_worker.py
```

### Docker Deployment

```bash
docker build -t hsl-spark-worker .
docker run -e REDIS_HOST=<host> -e REDIS_PORT=<port> hsl-spark-worker
```

### GCP Dataproc

```bash
gcloud dataproc jobs submit pyspark \
  --cluster=hsl-cluster \
  --region=europe-west1 \
  run_spark_worker.py
```

## Data Flow

```
Kafka
  ↓
read_from_kafka (kafka_reader.py)
  ↓
clean_bus_data (data_pipeline.py)
  ↓
┌─────────────────────────────────────────────────────┐
│                                                     │
├─→ Redis (real-time UI)                            │
│   ├─ write_position_to_redis_query                │
│   └─ write_speed_avg_to_redis_query               │
│                                                     │
├─→ GCS Bronze (raw, partitioned by date)           │
│   └─ bronze_layer (storage_writer.py)             │
│                                                     │
└─→ GCS Silver (cleaned, windowed, Delta Lake)      │
    └─ silver_layer (storage_writer.py)             │
```

## Key Features

### Data Validation
- Geographic bounds filtering (Helsinki area)
- Speed validation (MIN_SPEED to MAX_SPEED)
- Heading validation (MIN_HEADING to MAX_HEADING)
- Occupancy validation (non-negative)
- Null checks for unique vehicle ID

### Redis Caching
- Position data: latest coordinates, heading, speed
- Speed averages: 5-minute windowed aggregations
- Traffic status classification: NORMAL, LIGHT, HEAVY, GRIDLOCK, UNKNOWN
- Stuck detection: vehicles at speed < 4 km/h for ≥ 3 minutes
- 10-minute TTL on cache entries

### Storage Layers
- **Bronze**: Parquet format, partitioned by year/month/day
- **Silver**: Delta Lake format, UPSERT merge, partitioned by event_date
- Checkpoints ensure exactly-once semantics

## Configuration

All configuration is managed via `hsl_common/settings.py` and environment variables:

```python
# Kafka
SPARK_KAFKA_BOOTSTRAP_SERVERS  # e.g., localhost:9092
KAFKA_TOPIC                     # e.g., hsl.vp

# Redis
REDIS_HOST
REDIS_PORT
REDIS_PASSWORD                  # Optional

# GCS Paths
GCS_BRONZE_PATH
GCS_SILVER_PATH
SPARK_CHECKPOINT_DIR

# Geo Bounds (Helsinki)
LOCATION_LAT_MIN, LOCATION_LAT_MAX
LOCATION_LONG_MIN, LOCATION_LONG_MAX

# Speed/Heading
MIN_SPEED, MAX_SPEED
MIN_HEADING, MAX_HEADING
```

## Troubleshooting

**Redis Connection Errors**
- Check `REDIS_HOST` and `REDIS_PORT` environment variables
- Verify Redis cluster is running and accessible from Spark workers

**Kafka Read Timeout**
- Verify topic exists: `kafka-topics --describe --topic <KAFKA_TOPIC>`
- Check bootstrap server connectivity
- Inspect Kafka broker logs

**GCS Permission Errors**
- Ensure Dataproc service account has Storage Object Creator/Viewer roles
- Verify bucket paths in `GCS_BRONZE_PATH` and `GCS_SILVER_PATH`

**Memory Issues**
- Adjust Spark executor memory in `spark_session.py`
- Reduce batch size or window size if needed

## Monitoring

- **Structured Logs**: All modules use `get_logger_instance(__name__)`
- **Spark UI**: Available at `localhost:4040` (local) or cluster master URL
- **Redis Monitor**: `redis-cli monitor` to watch incoming writes
- **Checkpoint Status**: Check GCS checkpoint directories for lag metrics

## Testing

To test individual modules locally:

```python
from schemas import VP_SCHEMA, BUS_SCHEMA
from spark_session import create_spark_session
from kafka_reader import read_from_kafka
from data_pipeline import clean_bus_data

spark = create_spark_session()
df = read_from_kafka(spark, starting_offsets="earliest")
clean_df = clean_bus_data(df)
clean_df.show()
```
