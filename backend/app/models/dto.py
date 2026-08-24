"""Request/response data-transfer objects for the analyze-log endpoint.

Defines the Pydantic v2 schemas used by the API layer to validate incoming
requests and to serialize analysis results back to the caller. Keeping these
DTOs isolated from ORM models preserves the layering boundary described in the
design document (models layer owns the HTTP contract, not persistence).
"""

from pydantic import BaseModel, Field, field_validator

# API-layer cap for incoming cleaned_log content. Set above the preprocessor's
# 8000-char output cap (preprocess.py MAX_CLEANED_LOG_CHARS) to accommodate
# logs submitted directly to the API while still guarding the LLM payload budget.
CLEANED_LOG_MAX_LENGTH = 10000


class AnalyzeLogRequest(BaseModel):
    """Incoming payload for ``POST /api/analyze-log``.

    Attributes:
        build_number: Identifier of the failed build. Must be non-empty.
        cleaned_log: Preprocessed log content to analyze. Must be non-empty,
            not blank after trimming, and at most ``CLEANED_LOG_MAX_LENGTH``
            characters.
        job_name: CI/CD job name (e.g. Jenkins job name). Used by the backend
            to compose notification messages. Optional — notifications fall back
            to build_number when absent.
        build_url: Direct URL to the CI/CD build console log. Included as a
            link in Slack/Teams notifications. Optional — omitted from
            notification cards when blank.
    """

    build_number: str = Field(min_length=1)
    cleaned_log: str = Field(min_length=1, max_length=CLEANED_LOG_MAX_LENGTH)
    job_name: str = Field(default="")
    build_url: str = Field(default="")

    @field_validator("cleaned_log")
    @classmethod
    def not_blank(cls, value: str) -> str:
        """Reject a ``cleaned_log`` that is empty once whitespace is trimmed.

        Args:
            value: The raw ``cleaned_log`` value provided in the request.

        Returns:
            The original value when it contains non-whitespace characters.

        Raises:
            ValueError: If the value is blank after trimming.
        """
        if not value.strip():
            raise ValueError("cleaned_log must not be empty")
        return value


class AnalysisResult(BaseModel):
    """Result returned after a successful analysis.

    Attributes:
        text: The plain-text analysis produced by the LLM provider.
        provider: The LLM provider that handled the request.
        model: Concrete model/deployment returned by the gateway.
    """

    text: str
    provider: str
    model: str = ""
