"""AI Ops Log Analyzer backend application package.

Top-level package for the FastAPI backend that analyzes failed CI/CD build
logs and returns structured Markdown diagnostics.

The package follows a layered architecture with a one-directional dependency
flow (see design document, section "Kiến trúc phân lớp Backend"):

    api (HTTP) -> core (business logic) -> repository (abstraction) -> db

Cross-cutting modules (``deps``, ``logging_config``) wire the layers together
without embedding business logic in the HTTP layer.
"""
