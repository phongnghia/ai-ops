.PHONY: build test build-demo test-demo build-python-demo test-python-demo

# AI Ops backend (Python)

# Validate that the Python backend source compiles before deployment.
build:
	python3 -m compileall -q backend/app

test:
	python3 -m pytest -q backend

# Demo Spring Boot order-service (Java — runs inside Docker)
#
# No Java or Maven installation required on the host.
# Docker pulls maven:3.9.6-eclipse-temurin-21-alpine and runs the build
# inside the container. The test target is expected to FAIL (3 intentional
# test failures) and produce a Maven Surefire log for AI Ops analysis.

build-demo:
	docker build --target test --tag order-service:test demo-app/java-order-service 2>&1; exit $$?

test-demo:
	docker build --target test --tag order-service:test demo-app/java-order-service 2>&1; exit $$?

# Demo Python inventory-service (Python — runs inside Docker)
#
# No Python installation required on the host.
# BUG #1 (NameError) and BUG #2 (ZeroDivisionError) always fail.
# BUG #3 (RuntimeError in apply_bulk_discount) fails ~50% of runs.
# Run multiple times to observe the intermittent failure.

test-python-demo:
	docker build --target test --tag inventory-service:test \
		demo-app/python-inventory-service 2>&1; exit $$?
