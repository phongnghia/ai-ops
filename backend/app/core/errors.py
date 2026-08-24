"""Domain exceptions for the analysis flow.

Defines specific exception classes raised by the business logic layer so that
callers can react to well-defined failure categories instead of catching a
generic ``Exception``. Each exception has a clear domain meaning:

- ``GatewayError`` maps to HTTP 502 at the API boundary.
- ``RepositorySaveError`` is caught inside the service (best-effort persistence)
  and does not reach the client.
- ``RetrievalError`` is caught inside the service so RAG retrieval failures do
  not break the main analysis flow.
"""


class DomainError(Exception):
    """Base class for all domain-level exceptions in the analysis flow."""


class GatewayError(DomainError):
    """Raised when the LLM gateway call cannot produce a usable result.

    Covers the gateway returning an error, being unreachable, or returning a
    successful response whose text content cannot be extracted or parsed. The
    API layer maps this exception to HTTP 502 without leaking internal details.
    """


class RepositorySaveError(DomainError):
    """Raised when persisting an analysis record to the database fails.

    Caught inside ``AnalysisService`` as a best-effort save: the analysis result
    is still returned to the caller with HTTP 200 and the failure is logged at
    ERROR level without the ``cleaned_log`` content.
    """


class RetrievalError(DomainError):
    """Raised when retrieving RAG context from the database fails or times out.

    Caught inside ``AnalysisService`` so the analysis continues with an empty
    context; the failure is logged at WARN level.
    """
