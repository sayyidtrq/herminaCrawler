FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# curl is required by the docker-compose healthcheck. Chromium and its
# distribution-matched driver keep Selenium independent from runtime downloads.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        chromium \
        chromium-driver \
        curl \
        xauth \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
COPY apps/api/requirements.txt /app/apps/api/requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/apps/api/requirements.txt

COPY app /app/app
COPY apps /app/apps
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
COPY scripts /app/scripts
COPY entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh /app/scripts/run_crawl_worker.sh \
    && mkdir -p /app/exports

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
