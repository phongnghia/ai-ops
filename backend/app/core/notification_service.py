"""Notification service for build failure alerts.

Sends structured build failure notifications to Microsoft Teams and/or Slack
after an AI analysis completes. Both channels are optional and controlled by
configuration flags — a missing or disabled channel is skipped silently.

Design decisions:
- Notification failures are always swallowed and logged at WARN level. A failed
  webhook must never propagate to the caller or affect the analysis response.
- Each channel has its own formatter so the output matches the rendering
  capabilities of that platform (Teams plain text, Slack Block Kit mrkdwn).
- HTTP calls use httpx (available transitively via the openai dependency) with
  an explicit timeout so a slow webhook cannot stall the response thread.
- This service depends only on AppConfig and the standard library — no circular
  imports with other core modules.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from app.db.config import AppConfig

logger = logging.getLogger(__name__)

# Maximum characters of analysis text included in a notification card.
# Teams and Slack both have message size limits; this keeps payloads safe.
_ANALYSIS_MAX_CHARS = 2000

# Timeout for each outbound webhook HTTP call (seconds).
# 15s gives webhook endpoints enough time to respond under normal load while
# still bounding the worst case. Notifications run after the analysis result
# is already built, so this only adds latency on failure paths.
_WEBHOOK_TIMEOUT_SECONDS = 15

# Section labels — must stay in sync with prompts.py.
_SECTION_PROBLEM = "🚨 Problem"
_SECTION_ROOT_CAUSE = "🔍 Root Cause"
_SECTION_FIX_STEPS = "🛠️ Fix Steps"
_ALL_SECTIONS = (_SECTION_PROBLEM, _SECTION_ROOT_CAUSE, _SECTION_FIX_STEPS)


@dataclass(frozen=True)
class NotificationContext:
    """All data needed to compose a build failure notification.

    Attributes:
        job_name: CI/CD job name (e.g. Jenkins job name).
        build_number: Build identifier.
        build_url: Direct URL to the build console log.
        analysis_text: Plain-text AI analysis returned by the LLM.
        provider: LLM provider that produced the analysis.
        model: Concrete model used.
        request_id: Correlation ID for log tracing.
    """

    job_name: str
    build_number: str
    build_url: str
    analysis_text: str
    provider: str
    model: str
    request_id: str


class NotificationService:
    """Sends build failure notifications to Teams and Slack.

    Both channels are guarded by their respective enable flags in AppConfig.
    A channel with no webhook URL configured is skipped with a warning log
    even if its enable flag is set.

    Notification failures are never propagated — the analysis result is always
    returned to the caller regardless of notification outcome.
    """

    def __init__(self, config: AppConfig) -> None:
        """Create a service bound to the given configuration.

        Args:
            config: Typed application config; notification flags and webhook
                URLs are read from here at call time, not at construction.
        """
        self._config = config

    def notify(self, ctx: NotificationContext) -> None:
        """Send notifications to all enabled channels.

        Each channel is attempted independently — a failure on one channel
        does not prevent the other from being sent.

        Args:
            ctx: All data needed to compose the notification messages.
        """
        sections = _parse_sections(ctx.analysis_text)

        if self._config.slack_notify_enable:
            self._send_slack(ctx, sections)

        if self._config.teams_notify_enable:
            self._send_teams(ctx, sections)

    def _send_slack(
        self,
        ctx: NotificationContext,
        sections: dict[str, str],
    ) -> None:
        """Send a Slack Block Kit notification.

        Args:
            ctx: Notification context.
            sections: Parsed analysis sections.
        """
        if not self._config.slack_webhook_url:
            logger.warning(
                "Slack notification skipped: SLACK_NOTIFY_ENABLE=true but SLACK_WEBHOOK_URL is not set",
                extra={"event": "NOTIFICATION_SKIPPED", "channel": "slack", "request_id": ctx.request_id},
            )
            return

        payload = _build_slack_payload(ctx, sections)
        self._post(
            url=self._config.slack_webhook_url,
            payload=payload,
            channel="slack",
            request_id=ctx.request_id,
        )

    def _send_teams(
        self,
        ctx: NotificationContext,
        sections: dict[str, str],
    ) -> None:
        """Send a Teams Power Automate webhook notification.

        Args:
            ctx: Notification context.
            sections: Parsed analysis sections.
        """
        if not self._config.teams_webhook_url:
            logger.warning(
                "Teams notification skipped: TEAMS_NOTIFY_ENABLE=true but TEAMS_WEBHOOK_URL is not set",
                extra={"event": "NOTIFICATION_SKIPPED", "channel": "teams", "request_id": ctx.request_id},
            )
            return

        payload = _build_teams_payload(ctx, sections)
        self._post(
            url=self._config.teams_webhook_url,
            payload=payload,
            channel="teams",
            request_id=ctx.request_id,
        )

    def _post(
        self,
        url: str,
        payload: dict,
        channel: str,
        request_id: str,
    ) -> None:
        """POST a JSON payload to a webhook URL.

        Never raises — all transport and HTTP errors are caught, logged at
        WARN level, and swallowed so a notification failure cannot propagate.

        Args:
            url: Webhook endpoint URL.
            payload: JSON-serialisable notification payload.
            channel: Human-readable channel name used in log records.
            request_id: Correlation ID for log tracing.
        """
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=_WEBHOOK_TIMEOUT_SECONDS) as resp:
                logger.info(
                    "Notification sent",
                    extra={
                        "event": "NOTIFICATION_SENT",
                        "channel": channel,
                        "http_status": resp.status,
                        "request_id": request_id,
                    },
                )
        except urllib.error.HTTPError as exc:
            logger.warning(
                "Notification failed",
                extra={
                    "event": "NOTIFICATION_FAILED",
                    "channel": channel,
                    "http_status": exc.code,
                    "reason": exc.reason,
                    "request_id": request_id,
                },
            )
        except Exception as exc:
            logger.warning(
                "Notification failed",
                extra={
                    "event": "NOTIFICATION_FAILED",
                    "channel": channel,
                    "reason": str(exc),
                    "request_id": request_id,
                },
            )


def _parse_sections(text: str) -> dict[str, str]:
    """Split plain-text AI output into named sections.

    The LLM is instructed to use bare section labels on their own line.
    Falls back to placing the full text under the Problem section when no
    labels are found.

    Args:
        text: Raw analysis text from the LLM.

    Returns:
        Dict mapping each section label to its content string.
    """
    sections: dict[str, str] = {s: "" for s in _ALL_SECTIONS}
    current: str | None = None

    for line in text.splitlines():
        stripped = line.strip()
        if stripped in sections:
            current = stripped
            continue
        if current is not None:
            sections[current] = (sections[current] + "\n" + line).lstrip("\n")

    if not any(sections.values()):
        sections[_SECTION_PROBLEM] = text.strip()

    return {k: v.strip() for k, v in sections.items()}


def _truncate(text: str, max_chars: int = _ANALYSIS_MAX_CHARS) -> str:
    """Truncate text to at most max_chars characters, appending '...' if cut.

    Args:
        text: Input text.
        max_chars: Maximum allowed length.

    Returns:
        The original text or a truncated version ending with '...'.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def _to_slack_mrkdwn(sections: dict[str, str]) -> str:
    """Convert parsed sections to Slack mrkdwn format.

    Section labels become *bold* lines. The LLM is instructed to wrap technical
    terms in backticks, which Slack renders as inline code — no further escaping
    is needed. Teams requires a different formatter because it ignores mrkdwn.

    Args:
        sections: Parsed analysis sections.

    Returns:
        Formatted mrkdwn string for a Slack section block.
    """
    parts: list[str] = []
    for label, content in sections.items():
        if content:
            parts.append(f"*{label}*")
            parts.append(content)
            parts.append("")
    return "\n".join(parts).strip()


def _to_teams_plain(sections: dict[str, str], ai_meta: str) -> str:
    """Convert parsed sections to plain text for Teams Power Automate.

    Teams renders no markup in Power Automate webhooks — section labels stand
    out naturally via their emoji prefix.

    Args:
        sections: Parsed analysis sections.
        ai_meta: Provider/model metadata line.

    Returns:
        Plain text body for the Teams message.
    """
    parts = [ai_meta, ""]
    for label, content in sections.items():
        if content:
            parts.append(label)
            parts.append(content)
            parts.append("")
    return "\n".join(parts).strip()


def _build_slack_payload(ctx: NotificationContext, sections: dict[str, str]) -> dict:
    """Build the Slack Block Kit webhook payload.

    Args:
        ctx: Notification context.
        sections: Parsed analysis sections.

    Returns:
        JSON-serialisable Slack Block Kit payload dict.
    """
    ai_context = f"*Provider:* {ctx.provider}  |  *Model:* {ctx.model}"
    slack_text = _truncate(_to_slack_mrkdwn(sections)) or "No AI analysis available."

    return {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Build Failed: {ctx.job_name} #{ctx.build_number}",
                    "emoji": True,
                },
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": ai_context}],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": slack_text},
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Build Log", "emoji": True},
                        "url": ctx.build_url,
                        "style": "danger",
                    }
                ],
            },
        ]
    }


def _build_teams_payload(ctx: NotificationContext, sections: dict[str, str]) -> dict:
    """Build the Teams Power Automate webhook payload.

    Teams Power Automate webhooks expect a plain JSON body with a single "text"
    field — they do not support Adaptive Cards or Block Kit. Markdown-like syntax
    is not rendered, so section emoji labels serve as the only visual structure.

    Args:
        ctx: Notification context.
        sections: Parsed analysis sections.

    Returns:
        JSON-serialisable Teams payload dict.
    """
    ai_meta = f"Provider: {ctx.provider} | Model: {ctx.model}"
    body = _truncate(_to_teams_plain(sections, ai_meta))

    return {
        "text": (
            f"Build Failed: {ctx.job_name} #{ctx.build_number}\n\n"
            f"{body}\n\n"
            f"View Build Log: {ctx.build_url}"
        )
    }
