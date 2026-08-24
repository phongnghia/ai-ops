#!/usr/bin/env python3
"""Generate /tmp/litellm-config.yaml from enabled provider environment flags.

Reads OLLAMA_PROVIDER_ENABLE, AZURE_FOUNDRY_PROVIDER_ENABLE, and
GOOGLE_GEMINI_PROVIDER_ENABLE to build a LiteLLM config that includes only
the active providers under the shared 'log-analyzer' model group.

Priority order (when multiple providers are enabled):
  1. Azure AI Foundry  — fastest, cloud GPU
  2. Google Gemini     — fast, cloud GPU
  3. Ollama            — local CPU, slowest

The first provider in the list is primary; LiteLLM falls back to the next
on failure when multiple providers share the same model_name.

Usage (called by docker-compose litellm entrypoint):
  python3 /app/generate_config.py > /tmp/litellm-config.yaml
"""

from __future__ import annotations

import os
import sys

# Cloud providers respond within seconds; this is generous headroom for
# network latency and gateway processing without blocking inference.
_CLOUD_PROVIDER_TIMEOUT_SECONDS = 60

# Ollama runs inference on CPU which can take 60-120s on a 7B parameter model.
# The timeout is set higher so slow hardware can still complete a request.
_OLLAMA_TIMEOUT_SECONDS = 180

# Module-level env reads are intentional: this is a one-shot config generator
# called by docker-compose, not a library. Ollama defaults to enabled (true)
# as the local/offline fallback; cloud providers default to disabled.
OLLAMA_ENABLE = os.environ.get("OLLAMA_PROVIDER_ENABLE", "true").strip().lower() == "true"
AZURE_ENABLE = os.environ.get("AZURE_FOUNDRY_PROVIDER_ENABLE", "false").strip().lower() == "true"
GOOGLE_ENABLE = os.environ.get("GOOGLE_GEMINI_PROVIDER_ENABLE", "false").strip().lower() == "true"


def _build_model_entries() -> list[str]:
    """Build the model_list YAML entries for all enabled providers.

    Returns:
        Ordered list of YAML strings, highest-priority provider first.
    """
    entries: list[str] = []

    if AZURE_ENABLE:
        azure_model = os.environ.get("AZURE_MODEL", "gpt-4o-mini")
        entries.append(f"""\
  - model_name: log-analyzer
    litellm_params:
      model: azure/{azure_model}
      api_base: os.environ/AZURE_API_BASE
      api_version: os.environ/AZURE_API_VERSION
      tenant_id: os.environ/AZURE_TENANT_ID
      client_id: os.environ/AZURE_CLIENT_ID
      client_secret: os.environ/AZURE_CLIENT_SECRET
      azure_scope: os.environ/AZURE_SCOPE
      timeout: {_CLOUD_PROVIDER_TIMEOUT_SECONDS}""")

    if GOOGLE_ENABLE:
        gemini_model = os.environ.get("GOOGLE_GEMINI_MODEL", "gemini-3.5-flash-lite")
        entries.append(f"""\
  - model_name: log-analyzer
    litellm_params:
      model: gemini/{gemini_model}
      api_key: os.environ/GOOGLE_GEMINI_API_KEY
      timeout: {_CLOUD_PROVIDER_TIMEOUT_SECONDS}""")

    if OLLAMA_ENABLE:
        ollama_model = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
        entries.append(f"""\
  - model_name: log-analyzer
    litellm_params:
      model: ollama_chat/{ollama_model}
      api_base: os.environ/OLLAMA_API_BASE
      timeout: {_OLLAMA_TIMEOUT_SECONDS}
      stream_timeout: {_OLLAMA_TIMEOUT_SECONDS}""")

    return entries


def _build_settings_lines() -> list[str]:
    """Build the litellm_settings YAML lines.

    The global request_timeout must cover the slowest enabled provider so
    requests are not cancelled before inference finishes.

    Returns:
        List of indented YAML setting lines.
    """
    request_timeout = _OLLAMA_TIMEOUT_SECONDS if OLLAMA_ENABLE else _CLOUD_PROVIDER_TIMEOUT_SECONDS
    lines = [
        f"  request_timeout: {request_timeout}",
        "  num_retries: 0",  # Retries are disabled: the backend handles degradation;
                             # LiteLLM retries could silently exceed the caller's timeout.
    ]
    if AZURE_ENABLE:
        lines.append("  enable_azure_ad_token_refresh: true")
    return lines


def main() -> int:
    """Generate and print the LiteLLM config YAML to stdout.

    Returns:
        0 on success; 1 when no provider is enabled (error written to stderr).
    """
    if not any([OLLAMA_ENABLE, AZURE_ENABLE, GOOGLE_ENABLE]):
        sys.stderr.write(
            "ERROR: No provider is enabled. Set at least one of "
            "OLLAMA_PROVIDER_ENABLE, AZURE_FOUNDRY_PROVIDER_ENABLE, "
            "or GOOGLE_GEMINI_PROVIDER_ENABLE to 'true'.\n"
        )
        return 1

    model_entries = _build_model_entries()
    settings_lines = _build_settings_lines()

    yaml_output = "model_list:\n"
    yaml_output += "\n".join(model_entries)
    yaml_output += "\n\nlitellm_settings:\n"
    yaml_output += "\n".join(settings_lines)
    yaml_output += "\n"

    sys.stdout.write(yaml_output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
