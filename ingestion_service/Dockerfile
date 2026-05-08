FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY ../shared_lib/ ./shared_lib/

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY run_ingestion.py .

CMD ["python", "run_ingestion.py"]