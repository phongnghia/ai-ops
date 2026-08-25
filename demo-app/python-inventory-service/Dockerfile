# Multi-stage build for the python-inventory-service demo.
#
# Stages:
#   test     — runs pytest. Expected to fail:
#              - BUG #1 (NameError: prodcut) — always fails
#              - BUG #2 (ZeroDivisionError)  — always fails on empty store
#              - BUG #3 (RuntimeError)       — flaky, fails ~50% of runs
#   runtime  — minimal image for running the service (only after bugs are fixed).
#
# Usage:
#   docker build --target test    -t inventory-service:test    .  # expected to fail
#   docker build --target runtime -t inventory-service:latest  .  # only after fixes

FROM python:3.12-alpine AS base

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Stage 1 — test
# Runs the full pytest suite. BUG #1 and BUG #2 always fail.
# BUG #3 (apply_bulk_discount) fails on ~50% of runs — run multiple times
# to observe the intermittent failure.
FROM base AS test
RUN python -m pytest tests/ -v --tb=short

# Stage 2 — runtime (reachable only when all bugs are fixed)
FROM base AS runtime
EXPOSE 8000
CMD ["uvicorn", "inventory.api:app", "--host", "0.0.0.0", "--port", "8000"]
