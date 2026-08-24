"""Log_Preprocessor pure logic for the AI Ops Log Analyzer.

This module exposes a single pure function, :func:`preprocess`, that turns raw
Jenkins console log lines into a compact ``cleaned_log`` string containing only
error-relevant content. The function performs no I/O so it can be exercised by
property-based tests. Reading the console log and writing the result are handled
by the surrounding bash wrapper (``preprocess_log.sh``), which is also
responsible for limiting the raw input to the last 100 lines before passing
it here.

Behavior:
    1. Keep only lines matching an error pattern, case-insensitive.
    2. Drop INFO lines that match no error pattern (implied by step 1).
    3. When nothing matches, fall back to the last ``min(50, n)`` original
       lines so there is always data to send.
    4. Cap the final ``cleaned_log`` at 8000 characters.
"""

from __future__ import annotations

ERROR_PATTERNS: tuple[str, ...] = ("ERROR", "FATAL", "Exception", "Failed")

FALLBACK_MAX_LINES: int = 50

MAX_CLEANED_LOG_CHARS: int = 8000

LINE_SEPARATOR: str = "\n"


def _matches_error_pattern(line: str) -> bool:
    """Return True when the line contains at least one error pattern.

    Args:
        line: A single raw log line.

    Returns:
        True if the line matches any pattern in ``ERROR_PATTERNS``
        (case-insensitive), otherwise False.
    """
    lowered_line = line.lower()
    return any(pattern.lower() in lowered_line for pattern in ERROR_PATTERNS)


def _filter_error_lines(raw_lines: list[str]) -> list[str]:
    """Keep only lines that match an error pattern.

    Args:
        raw_lines: The raw log lines to filter.

    Returns:
        The subset of ``raw_lines`` matching at least one error pattern.
    """
    return [line for line in raw_lines if _matches_error_pattern(line)]


def preprocess(raw_lines: list[str]) -> str:
    """Turn raw log lines into a compact, error-focused cleaned_log string.

    Keeps only error-relevant lines. When no line matches an error pattern,
    falls back to the last ``min(50, len(raw_lines))`` original lines so that
    downstream analysis always receives some context. The result is truncated
    to at most 8000 characters.

    Args:
        raw_lines: Raw Jenkins console log lines (already limited upstream to
            the last 100 lines of the build).

    Returns:
        The cleaned_log string, capped at ``MAX_CLEANED_LOG_CHARS`` characters.
    """
    error_lines = _filter_error_lines(raw_lines)

    if error_lines:
        return LINE_SEPARATOR.join(error_lines)[:MAX_CLEANED_LOG_CHARS]

    fallback_lines = raw_lines[-FALLBACK_MAX_LINES:]
    return LINE_SEPARATOR.join(fallback_lines)[:MAX_CLEANED_LOG_CHARS]


def _main() -> int:
    """CLI entry: read raw log lines from stdin, print cleaned_log to stdout.

    Reads the full stdin as newline-delimited log lines, runs :func:`preprocess`,
    and writes the result to stdout. This function always returns 0 — runtime
    errors propagate as exceptions and are not caught here.

    Returns:
        Process exit code (always 0).
    """
    import sys

    raw_lines = sys.stdin.read().splitlines()
    sys.stdout.write(preprocess(raw_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
