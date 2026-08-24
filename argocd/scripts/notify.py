#!/usr/bin/env python3
"""Format and print the AI analysis for an ArgoCD sync failure.

Reads AI_* environment variables exported by analyze.sh and prints a
structured plain-text summary to stdout. This output is captured by the
ArgoCD Notifications webhook handler and can be sent to Slack, Teams,
or any other channel configured in argocd-notifications-cm.yaml.

Exit code: 0 always.
"""

from __future__ import annotations

import os
import sys

_SEPARATOR = "━" * 52

SECTION_PROBLEM    = "🚨 Problem"
SECTION_ROOT_CAUSE = "🔍 Root Cause"
SECTION_FIX_STEPS  = "🛠️ Fix Steps"
ALL_SECTIONS = (SECTION_PROBLEM, SECTION_ROOT_CAUSE, SECTION_FIX_STEPS)


def get_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _parse_sections(text: str) -> dict[str, str]:
    """Split plain-text AI output into named sections."""
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


def _format_output(sections: dict[str, str], ai_meta: str, app_name: str) -> str:
    """Format the analysis for human-readable output."""
    inner_sep = "─" * 48
    lines = [
        _SEPARATOR,
        f"  AI OPS ANALYSIS — {app_name}",
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
    app_name = get_env("ARGOCD_APP_NAME", "unknown-app")

    if status != "ok":
        print("AI analysis unavailable — check backend logs for details.")
        return 0

    ai_meta = f"Provider: {provider} | Model: {model}"
    sections = _parse_sections(raw_analysis)
    print(_format_output(sections, ai_meta, app_name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
