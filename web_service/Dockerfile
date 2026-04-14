# HSL_BUS/web_service/Dockerfile
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY shared_lib /app/shared_lib
COPY web_service /app/web_service
WORKDIR /app/web_service

RUN pip install --no-cache-dir -r requirements.txt gunicorn

EXPOSE 8080

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 run_web:app