# Jewellery Image Studio: app + API + team console in one container.
#   docker compose up --build        (see RUN.md)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/data U2NET_HOME=/data/models
# libgomp1 is needed by the cut-out model's runtime (onnxruntime)
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY backend/requirements.txt backend/requirements-ai.txt ./
ARG WITH_AI=1
RUN pip install -r requirements.txt && if [ "$WITH_AI" = "1" ]; then pip install -r requirements-ai.txt; fi
COPY backend/ .
RUN rm -rf .venv .env data

# Safe defaults = test mode. Real settings come from backend/.env (compose) or the host's dashboard.
ENV DEV_MODE=1 AI_MODE=test

VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/health')"
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
