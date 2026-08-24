"""LiteLLM-backed implementation of the :class:`LLMClient` boundary.

Provides :class:`LiteLLMClient`, a concrete :class:`~app.llm.base.LLMClient`
that talks to the LiteLLM gateway through its OpenAI-compatible chat completions
API. Business logic in ``core`` depends only on the ``LLMClient`` Protocol, so
this concrete client can be swapped for another provider without touching
``core``.

Design constraints:
- Every gateway call has an explicit timeout so a hung provider cannot block
  the request thread indefinitely.
- The gateway is reached through the shared model group ``log-analyzer``; the
  client is unaware of the underlying provider (Azure/Ollama/Gemini), which
  LiteLLM selects and fails over internally.
- Any transport error, gateway error, or a successful response whose text
  content cannot be extracted is surfaced as :class:`GatewayError` so the API
  layer can map it to HTTP 502 without leaking internal details.
"""

from __future__ import annotations

from openai import OpenAI, OpenAIError

from app.core.errors import GatewayError
from app.llm.base import LLMResult

# Model group configured in litellm/generate_config.py. The backend always
# targets this group; LiteLLM resolves and fails over between the concrete
# providers based on which are enabled.
MODEL_GROUP = "log-analyzer"

# Fallback provider label when LiteLLM does not resolve a concrete model name.
# Aliased from MODEL_GROUP so both the routing target and the fallback label
# are kept in sync without a separate literal.
DEFAULT_PROVIDER = MODEL_GROUP

# Generic, non-leaky message returned to callers for every gateway failure.
_GATEWAY_UNAVAILABLE_MESSAGE = "LLM gateway unavailable"


class LiteLLMClient:
    """LLMClient implementation backed by the LiteLLM OpenAI-compatible gateway.

    Conforms structurally to the :class:`~app.llm.base.LLMClient` Protocol.
    Dependencies (gateway URL, API key, timeout) are supplied via the
    constructor rather than read from global config, keeping the client
    decoupled and unit-testable.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout_seconds: int,
        *,
        model_group: str = MODEL_GROUP,
    ) -> None:
        """Create a client bound to a LiteLLM gateway.

        Args:
            base_url: Base URL of the LiteLLM gateway (e.g. ``http://litellm:4000``).
            api_key: Master key used to authenticate against the gateway.
            timeout_seconds: Timeout, in seconds, applied to every completion
                call. Enforced by the underlying OpenAI client.
            model_group: LiteLLM model group to target. Defaults to
                ``log-analyzer`` and is injectable for testing.
        """
        self._model_group = model_group
        # Owning the timeout at the client level applies it uniformly to every
        # request without per-call bookkeeping.
        self._client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout_seconds,
        )

    def complete(self, messages: list[dict]) -> LLMResult:
        """Request a completion from the gateway for the given chat messages.

        Args:
            messages: OpenAI-compatible chat messages (each a dict with at least
                ``role`` and ``content``) describing the system prompt and user
                context.

        Returns:
            An :class:`LLMResult` with the extracted completion ``text`` and the
            ``provider`` (resolved model) that served the request.

        Raises:
            GatewayError: If the gateway call fails, is unreachable, or returns a
                response whose text content cannot be extracted. The message is
                intentionally generic to avoid leaking internals.
        """
        try:
            response = self._client.chat.completions.create(
                model=self._model_group,
                messages=messages,
            )
        except OpenAIError as exc:
            # Do not attach the original message/detail to avoid leaking
            # endpoints or credentials to the caller.
            raise GatewayError(_GATEWAY_UNAVAILABLE_MESSAGE) from exc

        return self._to_result(response)

    def _to_result(self, response: object) -> LLMResult:
        """Extract completion text and provider from a gateway response.

        Args:
            response: The object returned by the chat completions call.

        Returns:
            An :class:`LLMResult` built from the first choice's message content.

        Raises:
            GatewayError: If the response shape is unexpected or the text
                content is missing or empty.
        """
        text = self._extract_text(response)
        if not text or not text.strip():
            # A structurally valid but content-less response is unusable; treat
            # it as a gateway failure rather than returning an empty analysis.
            raise GatewayError(_GATEWAY_UNAVAILABLE_MESSAGE)

        model = self._extract_model(response)
        provider = self._provider_from_model(model)
        return LLMResult(text=text, provider=provider, model=model)

    @staticmethod
    def _extract_text(response: object) -> str | None:
        """Return ``choices[0].message.content`` or ``None`` if unparseable."""
        try:
            return response.choices[0].message.content
        except (AttributeError, IndexError, TypeError):
            return None

    @staticmethod
    def _extract_model(response: object) -> str:
        """Return the concrete model/deployment reported by LiteLLM."""
        model = getattr(response, "model", None)
        if isinstance(model, str) and model.strip():
            return model.strip()
        return MODEL_GROUP

    @staticmethod
    def _provider_from_model(model: str) -> str:
        """Map a concrete model name to a stable provider identifier.

        Gemini model names do not contain a recognizable provider token in the
        LiteLLM response — they fall through to DEFAULT_PROVIDER ("log-analyzer").
        This is acceptable because provider resolution is best-effort for logging
        and does not affect request routing.
        """
        lowered = model.lower()
        if "ollama" in lowered:
            return "ollama"
        if "azure" in lowered or "openai" in lowered:
            return "azure_foundry"
        # Gemini and unrecognised providers fall through to the model group name.
        return DEFAULT_PROVIDER
