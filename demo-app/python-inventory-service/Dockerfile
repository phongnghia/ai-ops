# Multi-stage build for the python-inventory-service demo.
#
# Stages:
#   compile  — syntax-check all Python files with py_compile. Fails on BUG #1
#              (SyntaxError: missing closing parenthesis in service.py).
#   test     — runs pytest. Fails on BUG #2 (NameError) and BUG #3 (ZeroDivisionError).
#   runtime  — minimal image for running the service (reachable only after bugs are fixed).
#
# Usage:
#   docker build --target compile -t inventory-service:compile .  # fails on SyntaxError
#   docker build --target test    -t inventory-service:test    .  # fails on runtime bugs
#   docker build --target runtime -t inventory-service:latest  .  # only after all fixes

FROM python:3.12-alpine AS base

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Stage 1 — compile
# Checks every .py file for syntax errors before running any tests.
# BUG #1 (SyntaxError in service.py) causes this stage to fail immediately.
FROM base AS compile
RUN python -m py_compile inventory/models.py inventory/api.py inventory/service.py

# Stage 2 — test
# Runs all pytest test cases.
# BUG #2 (NameError: prodcut) and BUG #3 (ZeroDivisionError) are caught here.
FROM compile AS test
RUN python -m pytest tests/ -v --tb=short

# Stage 3 — runtime (reachable only when all bugs are fixed)
FROM base AS runtime
EXPOSE 8000
CMD ["uvicorn", "inventory.api:app", "--host", "0.0.0.0", "--port", "8000"]
