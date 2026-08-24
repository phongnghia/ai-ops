"""Typed application configuration.

Single source of truth for environment-derived configuration. All environment
variables are read and validated exactly once at startup via :func:`get_config`,
producing an immutable, typed :class:`AppConfig` object. No other module reads
``os.environ`` directly — they depend on this typed config instead
(see ``coding-standards.md`` section 9.3).

Validation is fail-fast: any missing required value or out-of-range setting
raises :class:`ConfigError` at load time so the service refuses to start with an
invalid configuration rather than failing later during request handling.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import quote_plus

ENV_DATABASE_URL = "DATABASE_URL"
ENV_DB_HOST = "DB_HOST"
ENV_DB_PORT = "DB_PORT"
ENV_DB_NAME = "DB_NAME"
ENV_DB_USER = "DB_USER"
ENV_DB_PASSWORD = "DB_PASSWORD"
ENV_LITELLM_BASE_URL = "LITELLM_BASE_URL"
ENV_LITELLM_API_KEY = "LITELLM_API_KEY"
ENV_SIMILARITY_SEARCH_MODE = "SIMILARITY_SEARCH_MODE"
ENV_RAG_TOP_N = "RAG_TOP_N"
ENV_RAG_CONTEXT_MAX_CHARS = "RAG_CONTEXT_MAX_CHARS"
ENV_LLM_TIMEOUT_SECONDS = "LLM_TIMEOUT_SECONDS"
ENV_DB_QUERY_TIMEOUT_SECONDS = "DB_QUERY_TIMEOUT_SECONDS"
ENV_APP_ENV = "APP_ENV"
ENV_OLLAMA_PROVIDER_ENABLE = "OLLAMA_PROVIDER_ENABLE"
ENV_AZURE_FOUNDRY_PROVIDER_ENABLE = "AZURE_FOUNDRY_PROVIDER_ENABLE"
ENV_GOOGLE_GEMINI_PROVIDER_ENABLE = "GOOGLE_GEMINI_PROVIDER_ENABLE"
ENV_GOOGLE_GEMINI_API_KEY = "GOOGLE_GEMINI_API_KEY"
ENV_GOOGLE_GEMINI_MODEL = "GOOGLE_GEMINI_MODEL"
ENV_AZURE_CLIENT_ID = "AZURE_CLIENT_ID"
ENV_AZURE_CLIENT_SECRET = "AZURE_CLIENT_SECRET"
ENV_AZURE_TENANT_ID = "AZURE_TENANT_ID"
ENV_AZURE_API_BASE = "AZURE_API_BASE"
ENV_AZURE_API_VERSION = "AZURE_API_VERSION"
ENV_AZURE_MODEL = "AZURE_MODEL"
ENV_SLACK_NOTIFY_ENABLE = "SLACK_NOTIFY_ENABLE"
ENV_SLACK_WEBHOOK_URL = "SLACK_WEBHOOK_URL"
ENV_TEAMS_NOTIFY_ENABLE = "TEAMS_NOTIFY_ENABLE"
ENV_TEAMS_WEBHOOK_URL = "TEAMS_WEBHOOK_URL"

DEFAULT_LITELLM_BASE_URL = "http://litellm:4000"
DEFAULT_SIMILARITY_SEARCH_MODE = "keyword"
DEFAULT_RAG_TOP_N = 3
DEFAULT_RAG_CONTEXT_MAX_CHARS = 4000
DEFAULT_LLM_TIMEOUT_SECONDS = 200
DEFAULT_DB_QUERY_TIMEOUT_SECONDS = 5
DEFAULT_APP_ENV = "production"
DEFAULT_DB_PORT = 5432
DEFAULT_OLLAMA_PROVIDER_ENABLE = True
DEFAULT_AZURE_FOUNDRY_PROVIDER_ENABLE = False
DEFAULT_GOOGLE_GEMINI_PROVIDER_ENABLE = False
DEFAULT_SLACK_NOTIFY_ENABLE = False
DEFAULT_TEAMS_NOTIFY_ENABLE = False

AI_PROVIDER_OLLAMA = "ollama"
AI_PROVIDER_AZURE_FOUNDRY = "azure_foundry"
AI_PROVIDER_GOOGLE_GEMINI = "google_gemini"

SIMILARITY_MODE_KEYWORD = "keyword"
SIMILARITY_MODE_VECTOR = "vector"
VALID_SIMILARITY_MODES = frozenset({SIMILARITY_MODE_KEYWORD, SIMILARITY_MODE_VECTOR})

APP_ENV_PRODUCTION = "production"
VALID_APP_ENVS = frozenset({"development", "staging", APP_ENV_PRODUCTION, "test"})

# Required together when DATABASE_URL is absent — validated as a group so the
# error message names all missing components at once rather than one at a time.
_DB_COMPONENT_VARS = (ENV_DB_HOST, ENV_DB_NAME, ENV_DB_USER, ENV_DB_PASSWORD)


class ConfigError(RuntimeError):
    """Raised when environment configuration is missing or invalid.

    Aggregates all validation problems so the operator sees every issue at once
    instead of fixing them one restart at a time.
    """


@dataclass(frozen=True)
class AppConfig:
    """Immutable, typed application configuration.

    Attributes:
        database_url: SQLAlchemy-compatible PostgreSQL connection URL.
        litellm_base_url: Base URL of the LiteLLM gateway (OpenAI-compatible).
        litellm_api_key: Master key used to authenticate against the gateway.
        similarity_search_mode: RAG search mode, ``keyword`` or ``vector``.
        rag_top_n: Maximum number of similar records used as RAG context.
        rag_context_max_chars: Maximum total length of the assembled RAG context.
        llm_timeout_seconds: Timeout applied to every LLM gateway call.
        db_query_timeout_seconds: Statement timeout applied to database queries.
        app_env: Deployment environment name controlling log verbosity.
        ai_provider: Active LLM provider (derived from enable flags at startup).
        slack_notify_enable: Whether to send Slack notifications after analysis.
        slack_webhook_url: Slack incoming webhook URL.
        teams_notify_enable: Whether to send Teams notifications after analysis.
        teams_webhook_url: Teams Power Automate webhook URL.
    """

    database_url: str
    litellm_base_url: str
    litellm_api_key: str
    similarity_search_mode: str
    rag_top_n: int
    rag_context_max_chars: int
    llm_timeout_seconds: int
    db_query_timeout_seconds: int
    app_env: str
    ai_provider: str
    slack_notify_enable: bool
    slack_webhook_url: str
    teams_notify_enable: bool
    teams_webhook_url: str

    @property
    def is_production(self) -> bool:
        """Return whether the service runs in the production environment."""
        return self.app_env == APP_ENV_PRODUCTION

    @property
    def is_vector_search(self) -> bool:
        """Return whether semantic (vector) similarity search is enabled."""
        return self.similarity_search_mode == SIMILARITY_MODE_VECTOR


def _resolve_database_url(env: dict[str, str], errors: list[str]) -> str:
    """Resolve the database URL from ``DATABASE_URL`` or ``DB_*`` components.

    Args:
        env: The environment mapping to read from.
        errors: Accumulator that collects validation error messages.

    Returns:
        A SQLAlchemy connection URL, or an empty string if resolution failed
        (in which case an error message has been appended to ``errors``).
    """
    explicit_url = env.get(ENV_DATABASE_URL, "").strip()
    if explicit_url:
        return explicit_url

    missing = [name for name in _DB_COMPONENT_VARS if not env.get(name, "").strip()]
    if missing:
        errors.append(
            f"Database configuration is incomplete: set {ENV_DATABASE_URL} or all of "
            f"{ENV_DB_HOST}/{ENV_DB_NAME}/{ENV_DB_USER}/{ENV_DB_PASSWORD}. "
            f"Missing: {', '.join(missing)}."
        )
        return ""

    port = _read_int(env, ENV_DB_PORT, DEFAULT_DB_PORT, errors, minimum=1)
    user = quote_plus(env[ENV_DB_USER].strip())
    password = quote_plus(env[ENV_DB_PASSWORD].strip())
    host = env[ENV_DB_HOST].strip()
    name = env[ENV_DB_NAME].strip()
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"


def _read_int(
    env: dict[str, str],
    name: str,
    default: int,
    errors: list[str],
    *,
    minimum: int = 1,
) -> int:
    """Read a positive integer env var, falling back to ``default`` when unset.

    Args:
        env: The environment mapping to read from.
        name: The environment variable name.
        default: Value used when the variable is absent or blank.
        errors: Accumulator that collects validation error messages.
        minimum: Smallest allowed value (inclusive).

    Returns:
        The parsed integer, or ``default`` when parsing/validation fails.
    """
    raw = env.get(name, "").strip()
    if not raw:
        return default

    try:
        value = int(raw)
    except ValueError:
        errors.append(f"{name} must be an integer, got {raw!r}.")
        return default

    if value < minimum:
        errors.append(f"{name} must be >= {minimum}, got {value}.")
        return default

    return value


def _read_bool(env: dict[str, str], name: str, default: bool, errors: list[str]) -> bool:
    """Read a strict boolean environment flag.

    Accepts the truthy strings ``true``, ``1``, ``yes``, ``on`` and the
    falsy strings ``false``, ``0``, ``no``, ``off`` (all case-insensitive).
    Any other non-empty value appends an error and returns ``default``.

    Args:
        env: The environment mapping to read from.
        name: The environment variable name.
        default: Value used when the variable is absent or blank.
        errors: Accumulator that collects validation error messages.

    Returns:
        The parsed boolean, or ``default`` when parsing fails.
    """
    raw = env.get(name, "").strip().lower()
    if not raw:
        return default
    if raw in {"true", "1", "yes", "on"}:
        return True
    if raw in {"false", "0", "no", "off"}:
        return False
    errors.append(f"{name} must be true or false, got {raw!r}.")
    return default


def _read_choice(
    env: dict[str, str],
    name: str,
    default: str,
    allowed: frozenset[str],
    errors: list[str],
) -> str:
    """Read an enum-like env var constrained to ``allowed`` values.

    Args:
        env: The environment mapping to read from.
        name: The environment variable name.
        default: Value used when the variable is absent or blank.
        allowed: The set of acceptable values.
        errors: Accumulator that collects validation error messages.

    Returns:
        The variable's value when valid, or ``default`` when absent.
    """
    value = env.get(name, "").strip() or default
    if value not in allowed:
        errors.append(f"{name} must be one of {sorted(allowed)}, got {value!r}.")
    return value


def _read_required(env: dict[str, str], name: str, errors: list[str]) -> str:
    """Read a required non-empty env var, recording an error when missing.

    Args:
        env: The environment mapping to read from.
        name: The environment variable name.
        errors: Accumulator that collects validation error messages.

    Returns:
        The variable's value, or an empty string when missing (an error is
        appended so the caller can report all missing vars at once).
    """
    value = env.get(name, "").strip()
    if not value:
        errors.append(f"{name} is required but was not set.")
    return value


def _resolve_ai_provider(
    env: dict[str, str],
    errors: list[str],
) -> str:
    """Determine the active AI provider from enable flags.

    Azure Foundry is preferred over Gemini, which is preferred over Ollama,
    matching the priority order in litellm/generate_config.py. Required
    credentials for the chosen provider are validated here so startup fails
    fast with a clear error rather than at inference time.

    Args:
        env: The environment mapping to read from.
        errors: Accumulator that collects validation error messages.

    Returns:
        The active provider identifier string.
    """
    ollama_enabled = _read_bool(env, ENV_OLLAMA_PROVIDER_ENABLE, DEFAULT_OLLAMA_PROVIDER_ENABLE, errors)
    foundry_enabled = _read_bool(env, ENV_AZURE_FOUNDRY_PROVIDER_ENABLE, DEFAULT_AZURE_FOUNDRY_PROVIDER_ENABLE, errors)
    google_enabled = _read_bool(env, ENV_GOOGLE_GEMINI_PROVIDER_ENABLE, DEFAULT_GOOGLE_GEMINI_PROVIDER_ENABLE, errors)

    enabled = [p for p, on in (
        (AI_PROVIDER_OLLAMA, ollama_enabled),
        (AI_PROVIDER_AZURE_FOUNDRY, foundry_enabled),
        (AI_PROVIDER_GOOGLE_GEMINI, google_enabled),
    ) if on]

    if not enabled:
        errors.append(
            "Enable at least one AI provider: OLLAMA_PROVIDER_ENABLE, "
            "AZURE_FOUNDRY_PROVIDER_ENABLE, or GOOGLE_GEMINI_PROVIDER_ENABLE."
        )

    if foundry_enabled:
        for name in (
            ENV_AZURE_CLIENT_ID, ENV_AZURE_CLIENT_SECRET, ENV_AZURE_TENANT_ID,
            ENV_AZURE_API_BASE, ENV_AZURE_API_VERSION, ENV_AZURE_MODEL,
        ):
            _read_required(env, name, errors)

    if google_enabled:
        _read_required(env, ENV_GOOGLE_GEMINI_API_KEY, errors)

    if foundry_enabled:
        return AI_PROVIDER_AZURE_FOUNDRY
    if google_enabled:
        return AI_PROVIDER_GOOGLE_GEMINI
    return AI_PROVIDER_OLLAMA


def _resolve_notification_config(
    env: dict[str, str],
    errors: list[str],
) -> tuple[bool, str, bool, str]:
    """Read and validate notification channel configuration.

    Validates that a webhook URL is provided whenever the corresponding
    enable flag is set, so misconfigured notifications are caught at startup.

    Args:
        env: The environment mapping to read from.
        errors: Accumulator that collects validation error messages.

    Returns:
        Tuple of (slack_enable, slack_url, teams_enable, teams_url).
    """
    slack_enable = _read_bool(env, ENV_SLACK_NOTIFY_ENABLE, DEFAULT_SLACK_NOTIFY_ENABLE, errors)
    slack_url = env.get(ENV_SLACK_WEBHOOK_URL, "").strip()
    if slack_enable and not slack_url:
        errors.append(f"{ENV_SLACK_WEBHOOK_URL} is required when SLACK_NOTIFY_ENABLE=true.")

    teams_enable = _read_bool(env, ENV_TEAMS_NOTIFY_ENABLE, DEFAULT_TEAMS_NOTIFY_ENABLE, errors)
    teams_url = env.get(ENV_TEAMS_WEBHOOK_URL, "").strip()
    if teams_enable and not teams_url:
        errors.append(f"{ENV_TEAMS_WEBHOOK_URL} is required when TEAMS_NOTIFY_ENABLE=true.")

    return slack_enable, slack_url, teams_enable, teams_url


def load_config(env: dict[str, str] | None = None) -> AppConfig:
    """Read and validate configuration from the environment (fail-fast).

    Args:
        env: Optional environment mapping; defaults to ``os.environ``. Injecting
            a mapping keeps this function pure and unit-testable.

    Returns:
        A fully validated, immutable :class:`AppConfig`.

    Raises:
        ConfigError: If any required value is missing or any value is invalid.
            All problems are aggregated into a single error message.
    """
    source = os.environ if env is None else env
    errors: list[str] = []

    database_url = _resolve_database_url(source, errors)
    litellm_base_url = source.get(ENV_LITELLM_BASE_URL, "").strip() or DEFAULT_LITELLM_BASE_URL
    litellm_api_key = _read_required(source, ENV_LITELLM_API_KEY, errors)
    similarity_search_mode = _read_choice(
        source, ENV_SIMILARITY_SEARCH_MODE, DEFAULT_SIMILARITY_SEARCH_MODE,
        VALID_SIMILARITY_MODES, errors,
    )
    rag_top_n = _read_int(source, ENV_RAG_TOP_N, DEFAULT_RAG_TOP_N, errors)
    rag_context_max_chars = _read_int(source, ENV_RAG_CONTEXT_MAX_CHARS, DEFAULT_RAG_CONTEXT_MAX_CHARS, errors)
    llm_timeout_seconds = _read_int(source, ENV_LLM_TIMEOUT_SECONDS, DEFAULT_LLM_TIMEOUT_SECONDS, errors)
    db_query_timeout_seconds = _read_int(source, ENV_DB_QUERY_TIMEOUT_SECONDS, DEFAULT_DB_QUERY_TIMEOUT_SECONDS, errors)
    app_env = _read_choice(source, ENV_APP_ENV, DEFAULT_APP_ENV, VALID_APP_ENVS, errors)
    ai_provider = _resolve_ai_provider(source, errors)
    slack_enable, slack_url, teams_enable, teams_url = _resolve_notification_config(source, errors)

    if errors:
        raise ConfigError("Invalid application configuration:\n- " + "\n- ".join(errors))

    return AppConfig(
        database_url=database_url,
        litellm_base_url=litellm_base_url,
        litellm_api_key=litellm_api_key,
        similarity_search_mode=similarity_search_mode,
        rag_top_n=rag_top_n,
        rag_context_max_chars=rag_context_max_chars,
        llm_timeout_seconds=llm_timeout_seconds,
        db_query_timeout_seconds=db_query_timeout_seconds,
        app_env=app_env,
        ai_provider=ai_provider,
        slack_notify_enable=slack_enable,
        slack_webhook_url=slack_url,
        teams_notify_enable=teams_enable,
        teams_webhook_url=teams_url,
    )


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Return the process-wide configuration, loading it once on first use.

    The result is cached so the environment is read and validated exactly once
    per process. Call :func:`load_config` directly in tests to avoid the cache.

    Returns:
        The validated :class:`AppConfig` singleton.

    Raises:
        ConfigError: If the environment configuration is invalid.
    """
    return load_config()
