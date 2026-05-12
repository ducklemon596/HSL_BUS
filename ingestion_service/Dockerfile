FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY ingestion_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && rm -rf /root/.cache/pip

COPY shared_lib/ ./shared_lib/

COPY ingestion_service/ .

CMD ["python", "run_ingestion.py"]