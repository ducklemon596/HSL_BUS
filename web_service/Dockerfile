# HSL_BUS/ingestion_service/Dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY shared_lib /app/shared_lib
COPY ingestion_service /app/ingestion_service
WORKDIR /app/ingestion_service
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "run_ingestion.py"]