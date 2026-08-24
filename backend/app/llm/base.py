"""LLM client abstraction.

Defines :class:`LLMResult`, the value returned from a completion call, and
:class:`LLMClient`, the boundary ``core`` uses to reach a large language model.
The client is expressed as a :class:`typing.Protocol` so that business logic
depends on an abstraction rather than a concrete provider or transport.

Concrete implementations (e.g. a LiteLLM-gateway-backed client) are injected
into ``core`` via dependency injection, allowing providers to be swapped without
modifying ``core``.

``LLMResult`` is a plain :func:`dataclasses.dataclass` rather than a Pydantic
model so importing this abstraction does not pull in a validation dependency at
import time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class LLMResult:
    """Outcome of a single completion call.

    Attributes:
        text: The completion text extracted from the provider response.
        provider: Identifier of the LLM provider that actually served the
            request (e.g. the resolved model reported by the gateway).
        model: Concrete model/deployment returned by the gateway.
    """

    text: str
    provider: str
    model: str = ""


@runtime_checkable
class LLMClient(Protocol):
    """Boundary for requesting completions from a language model.

    Implementations must set an explicit timeout on the underlying call and
    must not leak sensitive details (API keys, internal endpoints) to callers.
    """

    def complete(self, messages: list[dict]) -> LLMResult:
        """Request a completion for the given chat messages.

        Args:
            messages: OpenAI-compatible chat messages (each a dict with at least
                ``role`` and ``content`` keys) describing the system prompt and
                user context to send to the model.

        Returns:
            An :class:`LLMResult` containing the completion ``text`` and the
            ``provider`` that served the request.
        """
        ...
