#!/usr/bin/env python3
"""Format and print the AI analysis to the Jenkins console log.

Notifications (Slack, Teams) are handled entirely by the backend service.
This script only formats the analysis text for human-readable console output.

When ANSI_CONSOLE=true (default) and the AnsiColor plugin is installed in
Jenkins, section headings are colored and backtick terms are highlighted.
Without the plugin, set ANSI_CONSOLE=false to get plain-text output using
Unicode box-drawing characters instead.

Reads from environment variables exported by analyze.sh:
    AI_STATUS     "ok" or "failed"
    AI_ANALYSIS   Plain-text analysis with section labels
    AI_PROVIDER   LLM provider name
    AI_MODEL      Concrete model used
    ANSI_CONSOLE  "true" to emit ANSI color codes (default: true)

Exit code: 0 always.
"""

from __future__ import annotations

import os
import re
import sys

# Console width used for separator lines. Wide enough to be visually distinct
# without wrapping on a standard 80-column terminal.
_CONSOLE_WIDTH = 52
_INNER_WIDTH = 48  # _CONSOLE_WIDTH minus 4 chars of indentation

_SEPARATOR = "━" * _CONSOLE_WIDTH

SECTION_PROBLEM    = "🚨 Problem"
SECTION_ROOT_CAUSE = "🔍 Root Cause"
SECTION_FIX_STEPS  = "🛠️ Fix Steps"
ALL_SECTIONS = (SECTION_PROBLEM, SECTION_ROOT_CAUSE, SECTION_FIX_STEPS)

# ANSI codes — only emitted when ANSI_CONSOLE=true.
_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_RED    = "\033[31m"
_YELLOW = "\033[33m"
_GREEN  = "\033[32m"
_CYAN   = "\033[36m"
_WHITE  = "\033[97m"

_SECTION_COLORS = {
    SECTION_PROBLEM:    _RED,
    SECTION_ROOT_CAUSE: _YELLOW,
    SECTION_FIX_STEPS:  _GREEN,
}


def get_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _ansi_enabled() -> bool:
    return get_env("ANSI_CONSOLE", "true").lower() != "false"


def _parse_sections(text: str) -> dict[str, str]:
    """Split plain-text AI output into named sections.

    Falls back to placing the full text under SECTION_PROBLEM when no
    section labels are found.
    """
    sections: dict[str, str] = {s: "" for s in ALL_SECTIONS}
    current: str | None = None

    for line in text.splitlines():
        stripped = line.strip()
        if stripped in sections:
            current = stripped
            continue
        if current is not None:
            sections[current] = (sections[current] + "\n" + line).lstrip("\n")

    if not any(sections.values()):
        sections[SECTION_PROBLEM] = text.strip()

    return {k: v.strip() for k, v in sections.items()}


def _highlight_backticks(line: str) -> str:
    """Wrap `backtick` spans in cyan — visible in terminals with ANSI support."""
    return re.sub(
        r"`([^`]+)`",
        lambda m: f"{_CYAN}`{m.group(1)}`{_RESET}",
        line,
    )


def _format_ansi(sections: dict[str, str], ai_meta: str) -> str:
    """Format with ANSI colors — requires AnsiColor plugin in Jenkins."""
    sep = f"{_DIM}{_SEPARATOR}{_RESET}"
    lines = [
        sep,
        f"  {_BOLD}{_WHITE}AI OPS LOG ANALYSIS{_RESET}",
        f"  {_DIM}{ai_meta}{_RESET}",
        sep,
    ]
    for label, content in sections.items():
        if not content:
            continue
        color = _SECTION_COLORS.get(label, _RESET)
        lines.append("")
        lines.append(f"  {_BOLD}{color}{label}{_RESET}")
        for line in content.splitlines():
            if line.strip():
                lines.append(f"  {_highlight_backticks(line)}")
            else:
                lines.append("")
    lines.append(f"\n{sep}")
    return "\n".join(lines)


def _format_plain(sections: dict[str, str], ai_meta: str) -> str:
    """Format with Unicode separators only — no ANSI, no plugin needed."""
    inner_sep = "─" * _INNER_WIDTH
    lines = [
        _SEPARATOR,
        "  AI OPS LOG ANALYSIS",
        f"  {ai_meta}",
        _SEPARATOR,
    ]
    for label, content in sections.items():
        if not content:
            continue
        lines.append("")
        lines.append(f"  {label}")
        lines.append(f"  {inner_sep}")
        for line in content.splitlines():
            cleaned = line.replace("`", "")
            lines.append(f"  {cleaned}" if cleaned.strip() else "")
    lines.append(f"\n{_SEPARATOR}")
    return "\n".join(lines)


def main() -> int:
    status = get_env("AI_STATUS")
    provider = get_env("AI_PROVIDER", "unknown")
    model = get_env("AI_MODEL", "unknown")
    raw_analysis = get_env("AI_ANALYSIS")

    if status != "ok":
        print("AI analysis unavailable — check backend logs for details.")
        return 0

    ai_meta = f"Provider: {provider} | Model: {model}"
    sections = _parse_sections(raw_analysis)

    if _ansi_enabled():
        print(_format_ansi(sections, ai_meta))
    else:
        print(_format_plain(sections, ai_meta))

    return 0


if __name__ == "__main__":
    sys.exit(main())
