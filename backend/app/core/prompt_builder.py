"""Prompt building for the log-analysis LLM interaction.

Assembles the OpenAI-compatible message list sent to the LLM provider: a
system message carrying the immutable ``SYSTEM_PROMPT`` and a user message that
embeds the build number, the cleaned log, and — only when available — a clearly
labeled block of similar past analyses (RAG context).
"""

from app.core.prompts import SYSTEM_PROMPT

# OpenAI chat message role strings — extracted to constants so a typo is a
# name error rather than a silent protocol violation.
ROLE_SYSTEM = "system"
ROLE_USER = "user"

BUILD_NUMBER_LABEL = "Build number"
CLEANED_LOG_LABEL = "Build log"
RAG_CONTEXT_LABEL = "Similar past analyses"


def build(
    cleaned_log: str,
    build_number: str,
    rag_context: str,
) -> list[dict[str, str]]:
    """Build the OpenAI-compatible message list for an analysis request.

    Combines the system prompt with a user message that always contains the
    build number and cleaned log verbatim. When ``rag_context`` is non-empty,
    a clearly labeled RAG context block is appended so the LLM can reference
    similar past analyses; when it is empty, the label is omitted entirely.

    Args:
        cleaned_log: The preprocessed build log to analyze. Included verbatim.
        build_number: Identifier of the failed build. Included verbatim.
        rag_context: Concatenated similar past analyses, already truncated by
            the caller. May be empty (or whitespace-only) when no context is
            available.

    Returns:
        A two-element list of messages: the system message followed by the
        user message, each shaped as ``{"role": ..., "content": ...}``.
    """
    user_content = _build_user_content(cleaned_log, build_number, rag_context)

    return [
        {"role": ROLE_SYSTEM, "content": SYSTEM_PROMPT},
        {"role": ROLE_USER, "content": user_content},
    ]


def _build_user_content(
    cleaned_log: str,
    build_number: str,
    rag_context: str,
) -> str:
    """Assemble the user message body from its labeled sections.

    The RAG context section is included only when ``rag_context`` carries
    meaningful content, so an empty context never introduces the label.

    Args:
        cleaned_log: The preprocessed build log, embedded verbatim.
        build_number: Identifier of the failed build, embedded verbatim.
        rag_context: Similar past analyses; skipped when empty/whitespace-only.

    Returns:
        The fully assembled user message content.
    """
    sections = [
        f"{BUILD_NUMBER_LABEL}: {build_number}",
        f"{CLEANED_LOG_LABEL}:\n{cleaned_log}",
    ]

    # Guard against whitespace-only context — omitting the label prevents the
    # LLM from seeing an empty "Similar past analyses:" section.
    if rag_context and rag_context.strip():
        sections.append(f"{RAG_CONTEXT_LABEL}:\n{rag_context}")

    return "\n\n".join(sections)
