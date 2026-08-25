# python-inventory-service — Demo Python App

A minimal FastAPI inventory service used to demonstrate real Python build failures
for AI Ops log analysis. The project contains three intentional bugs that produce
distinct failure types across two Docker build stages.

## Intentional bugs

| # | Location | Bug type | When detected | Error |
|---|---|---|---|---|
| 1 | `inventory/service.py` line 45 | SyntaxError | Compile stage (`--target compile`) | `SyntaxError: was never closed` — missing `)` on `raise KeyError(...)` |
| 2 | `inventory/service.py` line 62 | NameError | Test stage (`--target test`) | `NameError: name 'prodcut' is not defined` — typo in `calculate_total_value()` |
| 3 | `inventory/service.py` line 78 | ZeroDivisionError | Test stage (`--target test`) | `ZeroDivisionError: division by zero` — `average_price()` does not handle empty inventory |

## Build stages

```
base     — install dependencies
compile  — python -m py_compile on all source files  ← fails on BUG #1
test     — pytest tests/                              ← fails on BUG #2 + BUG #3
runtime  — uvicorn server                             ← only reachable after all fixes
```

## Run via Docker (from this directory)

```bash
# Fails on BUG #1 — SyntaxError
docker build --target compile -t inventory-service:compile .

# Fails on BUG #2 + BUG #3 (after fixing BUG #1)
docker build --target test -t inventory-service:test .
```

## Run via Makefile (from repo root)

```bash
make build-python-demo   # compile stage — fails on SyntaxError
make test-python-demo    # test stage   — fails on NameError + ZeroDivisionError
```

## Run via Jenkins

In the pipeline **Build with Parameters**:

```
DEMO_PROJECT = python-inventory-service               # compile + test
DEMO_PROJECT = python-inventory-service-compile-only  # compile only (SyntaxError)
```
