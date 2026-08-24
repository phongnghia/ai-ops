"""HTTP layer package.

Contains FastAPI routers that parse requests, delegate to the ``core`` layer,
and map domain errors to HTTP responses. This layer holds no business logic
and never accesses the database directly (see Requirements 7.1, 7.2).
"""
