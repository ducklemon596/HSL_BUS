FROM python:3.9-slim

WORKDIR /app

COPY shared_lib/ ./shared_lib/
RUN pip install --no-cache-dir -e "./shared_lib[kafka]"

COPY ingestion_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ingestion_service/run_ingestion.py .

ENV PYTHONPATH="/app"

CMD ["python", "run_ingestion.py"]