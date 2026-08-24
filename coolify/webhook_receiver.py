#!/usr/bin/env python3
"""Coolify webhook receiver for AI Ops Log Analyzer.

Coolify sends a JSON POST request to this endpoint when a deployment fails,
an application stops unexpectedly, a scheduled task fails, or other error
events occur. This receiver transforms the Coolify payload into the format
expected by POST /api/analyze-log and forwards it to the AI Ops backend.

Supported Coolify events that trigger analysis:
  deployment_failed   — application deployment failed
  status_changed      — application stopped unexpectedly
  container_stopped   — container stopped unexpectedly
  task_failed         — scheduled task failed
  backup_failed       — database backup failed
  server_unreachable  — Coolify cannot reach a server

Run:
  python3 webhook_receiver.py

The receiver listens on port 9000 by default. Configure the URL in Coolify
under: Settings → Notifications → Webhook → URL.

Environment variables:
  AI_OPS_BACKEND_URL   Backend service URL (default: http://localhost:8000)
  RECEIVER_PORT        Port to listen on (default: 9000)
  RECEIVER_SECRET      Optional shared secret to validate Coolify requests
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

AI_OPS_BACKEND_URL = os.environ.get("AI_OPS_BACKEND_URL", "http://localhost:8000").rstrip("/")
RECEIVER_PORT = int(os.environ.get("RECEIVER_PORT", "9000"))
RECEIVER_SECRET = os.environ.get("RECEIVER_SECRET", "")

ANALYZE_ENDPOINT = "/api/analyze-log"
REQUEST_TIMEOUT_SECONDS = 300

# Coolify events that represent failures worth analyzing.
FAILURE_EVENTS = frozenset({
    "deployment_failed",
    "status_changed",
    "container_stopped",
    "task_failed",
    "backup_failed",
    "server_unreachable",
})


def _build_cleaned_log(payload: dict) -> str:
    """Build a cleaned_log string from a Coolify webhook payload.

    Coolify does not include raw build logs in webhook payloads. This function
    constructs a structured diagnostic summary from the available metadata
    fields so the LLM has enough context to produce a meaningful analysis.
    """
    event = payload.get("event", "unknown")
    message = payload.get("message", "No message provided")

    lines = [
        f"Coolify Event: {event}",
        f"Message: {message}",
    ]

    if "application_name" in payload:
        lines.append(f"Application: {payload['application_name']}")
    if "project" in payload:
        lines.append(f"Project: {payload['project']}")
    if "environment" in payload:
        lines.append(f"Environment: {payload['environment']}")
    if "deployment_url" in payload:
        lines.append(f"Deployment URL: {payload['deployment_url']}")
    if "container_name" in payload:
        lines.append(f"Container: {payload['container_name']}")
    if "server_name" in payload:
        lines.append(f"Server: {payload['server_name']}")
    if "database_name" in payload:
        lines.append(f"Database: {payload['database_name']}")
        lines.append(f"Database type: {payload.get('database_type', 'unknown')}")
    if "task_name" in payload:
        lines.append(f"Task: {payload['task_name']}")
    if "output" in payload and payload["output"]:
        lines.append("")
        lines.append("Task output:")
        lines.append(payload["output"])
    if "error_output" in payload and payload["error_output"]:
        lines.append("")
        lines.append("ERROR:")
        lines.append(payload["error_output"])
    if "error_message" in payload and payload["error_message"]:
        lines.append("")
        lines.append("ERROR:")
        lines.append(payload["error_message"])

    return "\n".join(lines)


def _build_resource_name(payload: dict) -> str:
    """Extract a short resource name to use as the build_number field."""
    for key in ("application_name", "container_name", "task_name",
                "database_name", "server_name"):
        if payload.get(key):
            return str(payload[key])
    return payload.get("event", "coolify-event")


def _build_resource_url(payload: dict) -> str:
    """Extract the most relevant URL from the payload for the build_url field."""
    for key in ("deployment_url", "url", "fqdn"):
        if payload.get(key):
            val = str(payload[key])
            if not val.startswith("http"):
                val = f"https://{val}"
            return val
    return ""


def _forward_to_backend(payload: dict) -> tuple[int, str]:
    """Transform a Coolify payload and POST it to the AI Ops backend.

    Returns (http_status, response_body_or_error).
    """
    resource_name = _build_resource_name(payload)
    event = payload.get("event", "unknown")

    request_body = json.dumps({
        "build_number": resource_name,
        "job_name":     f"coolify/{resource_name}",
        "build_url":    _build_resource_url(payload),
        "cleaned_log":  _build_cleaned_log(payload),
    }).encode()

    req = urllib.request.Request(
        f"{AI_OPS_BACKEND_URL}{ANALYZE_ENDPOINT}",
        data=request_body,
        headers={
            "Content-Type": "application/json",
            "X-AI-Client":  "Coolify",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            body = resp.read().decode()
            logger.info(
                "Analysis complete for %s event on %s — provider: %s",
                event,
                resource_name,
                resp.headers.get("X-AI-Provider", "unknown"),
            )
            return resp.status, body
    except urllib.error.HTTPError as exc:
        logger.error("Backend returned HTTP %s for event %s", exc.code, event)
        return exc.code, str(exc)
    except Exception as exc:
        logger.error("Failed to reach backend for event %s: %s", event, exc)
        return 0, str(exc)


def _verify_signature(body: bytes, signature_header: str) -> bool:
    """Verify the HMAC-SHA256 signature when RECEIVER_SECRET is configured.

    Coolify signs webhook requests when a secret is configured. Skip
    verification when no secret is set so the receiver works without one.
    """
    if not RECEIVER_SECRET:
        return True
    if not signature_header:
        return False
    expected = hmac.new(
        RECEIVER_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature_header)


class CoolifyWebhookHandler(BaseHTTPRequestHandler):
    """HTTP handler that receives Coolify webhook notifications."""

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        signature = self.headers.get("X-Coolify-Signature", "")
        if not _verify_signature(body, signature):
            logger.warning("Invalid webhook signature — request rejected")
            self._respond(401, {"error": "Invalid signature"})
            return

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            logger.warning("Received invalid JSON payload")
            self._respond(400, {"error": "Invalid JSON"})
            return

        event = payload.get("event", "")
        success = payload.get("success", True)

        # Only analyze failure events — success events are acknowledged but
        # not forwarded to the backend.
        if success or event not in FAILURE_EVENTS:
            logger.info("Skipping non-failure event: %s (success=%s)", event, success)
            self._respond(200, {"status": "skipped", "event": event})
            return

        logger.info("Received failure event: %s", event)
        status, _ = _forward_to_backend(payload)

        if status == 200:
            self._respond(200, {"status": "analyzed", "event": event})
        else:
            self._respond(200, {"status": "backend_error", "event": event, "backend_status": status})

    def _respond(self, status: int, body: dict) -> None:
        response = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, fmt: str, *args: object) -> None:
        logger.info(fmt, *args)


def main() -> None:
    server = HTTPServer(("0.0.0.0", RECEIVER_PORT), CoolifyWebhookHandler)
    logger.info(
        "Coolify webhook receiver listening on port %d — forwarding to %s",
        RECEIVER_PORT,
        AI_OPS_BACKEND_URL,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Receiver stopped.")


if __name__ == "__main__":
    main()
