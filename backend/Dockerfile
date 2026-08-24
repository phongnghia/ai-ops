# syntax=docker/dockerfile:1
# Backend Service image for the AI Ops Log Analyzer.

FROM python:3.12.8-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv

WORKDIR /build

RUN python -m venv "${VIRTUAL_ENV}"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

COPY requirements.txt ./
RUN pip install --requirement requirements.txt

FROM python:3.12.8-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONPATH="/app" \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser alembic.ini ./alembic.ini
COPY --chown=appuser:appuser migrations ./migrations

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import os,urllib.request,sys; url='http://127.0.0.1:'+os.environ.get('APP_PORT','8000')+'/health'; sys.exit(0 if urllib.request.urlopen(url, timeout=4).status==200 else 1)"]

CMD alembic upgrade head && exec uvicorn app.main:app --host ${APP_HOST} --port ${APP_PORT}
