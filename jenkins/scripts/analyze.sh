#!/usr/bin/env bash
# analyze.sh — Request AI log analysis from the backend and export results.
#
# Reads the Jenkins build log, calls POST /api/analyze-log, and exports the
# following variables for the caller (Jenkinsfile post-failure block) to use
# for console output:
#
#   AI_ANALYSIS   Full analysis text returned by the backend
#   AI_PROVIDER   LLM provider that served the request
#   AI_MODEL      Concrete model used
#   AI_STATUS     "ok" on HTTP 200, "failed" otherwise
#
# Notification (Slack/Teams) is handled entirely by the backend — this script
# passes job_name and build_url in the request body so the backend can compose
# notification messages without needing those secrets on the pipeline side.
#
# Required environment variables (loaded from .env by the caller):
#   BACKEND_URL           Backend service URL (default: http://localhost:8000)
#   JENKINS_HOME          Jenkins home directory (default: /var/lib/jenkins)
#   JOB_NAME              Jenkins job name
#   BUILD_NUMBER          Jenkins build number
#   JENKINS_URL           Jenkins base URL (used to build the console link)
#   DEMO_PROJECT          "none" or a demo project name (e.g. java-order-service)
#   DEMO_FAIL_BUILD       "true" to use a synthetic error instead of the real log
#
# Optional:
#   BACKEND_URL_PARAM     Overrides BACKEND_URL when set
#   JENKINS_LOG_FILE      Explicit path to the Jenkins build log on disk
#
set -euo pipefail

readonly ANALYZE_ENDPOINT="/api/analyze-log"
readonly CURL_TIMEOUT_SECONDS=300
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
readonly PREPROCESS_SCRIPT="${SCRIPT_DIR}/preprocess_log.sh"

AI_ANALYSIS=""
AI_PROVIDER="unknown"
AI_MODEL="unknown"
AI_STATUS="failed"

_resolve_backend_url() {
    echo "${BACKEND_URL:-http://localhost:8000}"
}

_resolve_log_file() {
    local jenkins_home="${JENKINS_HOME:-/var/lib/jenkins}"
    echo "${JENKINS_LOG_FILE:-${jenkins_home}/jobs/${JOB_NAME}/builds/${BUILD_NUMBER}/log}"
}

_resolve_build_url() {
    local base="${JENKINS_URL:-http://localhost:8080}"
    # Ensure trailing slash before appending path segments.
    base="${base%/}/"
    echo "${base}job/${JOB_NAME}/${BUILD_NUMBER}/console"
}

_read_cleaned_log() {
    # Demo mode: run the preprocessor against the real build log of a named demo project.
    if [[ "${DEMO_PROJECT:-none}" != "none" ]]; then
        export JENKINS_LOG_FILE
        JENKINS_LOG_FILE="$(_resolve_log_file)"
        bash "${PREPROCESS_SCRIPT}"
        return
    fi

    # Synthetic failure mode: inject a hardcoded error without reading any log file.
    # Used for quick end-to-end testing of the AI pipeline without a real build failure.
    if [[ "${DEMO_FAIL_BUILD:-false}" == "true" ]]; then
        printf '%s\n' \
            'ERROR: Demo dependency installation failed' \
            'ModuleNotFoundError: No module named demo_dependency' \
            'Build step failed with exit code 1'
        return
    fi

    export JENKINS_LOG_FILE
    JENKINS_LOG_FILE="$(_resolve_log_file)"
    bash "${PREPROCESS_SCRIPT}"
}

# Build JSON via Python rather than shell string interpolation to safely handle
# newlines and special characters in cleaned_log without manual escaping.
# Values are passed through the environment, never as argv.
_build_request_body() {
    local cleaned_log="${1}"
    local build_url="${2}"
    BUILD_NUMBER_VALUE="${BUILD_NUMBER}" \
    JOB_NAME_VALUE="${JOB_NAME:-}" \
    BUILD_URL_VALUE="${build_url}" \
    CLEANED_LOG_VALUE="${cleaned_log}" \
    python3 -c '
import json, os
print(json.dumps({
    "build_number": os.environ["BUILD_NUMBER_VALUE"],
    "job_name":     os.environ["JOB_NAME_VALUE"],
    "build_url":    os.environ["BUILD_URL_VALUE"],
    "cleaned_log":  os.environ["CLEANED_LOG_VALUE"],
}))
'
}

_call_backend() {
    local backend_url="${1}"
    local request_body="${2}"
    local response_file response_headers http_status

    response_file="$(mktemp)"
    response_headers="$(mktemp)"

    http_status="$(
        curl \
            --silent \
            --show-error \
            --max-time "${CURL_TIMEOUT_SECONDS}" \
            --request POST \
            --header "Content-Type: application/json" \
            --header "X-AI-Client: Jenkins" \
            --data "${request_body}" \
            --output "${response_file}" \
            --dump-header "${response_headers}" \
            --write-out "%{http_code}" \
            "${backend_url}${ANALYZE_ENDPOINT}" \
        || echo "000"
    )"

    if [[ "${http_status}" == "200" ]]; then
        AI_STATUS="ok"
        AI_ANALYSIS="$(cat "${response_file}")"
        AI_PROVIDER="$(
            grep -iE "^x-ai-provider:" "${response_headers}" \
            | tr -d "\r" | cut -d: -f2- | xargs \
            || echo "unknown"
        )"
        AI_MODEL="$(
            grep -iE "^x-ai-model:" "${response_headers}" \
            | tr -d "\r" | cut -d: -f2- | xargs \
            || echo "unknown"
        )"
    else
        echo "AI analysis request failed — HTTP status: ${http_status}" >&2
    fi

    rm -f "${response_file}" "${response_headers}"
}

main() {
    local backend_url
    backend_url="$(_resolve_backend_url)"

    local build_url
    build_url="$(_resolve_build_url)"

    echo "AI analysis backend: ${backend_url}"

    command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }
    command -v curl    >/dev/null || { echo "curl is required"    >&2; exit 1; }
    [[ -f "${PREPROCESS_SCRIPT}" ]] || { echo "preprocess_log.sh not found: ${PREPROCESS_SCRIPT}" >&2; exit 1; }

    local cleaned_log
    cleaned_log="$(_read_cleaned_log)"

    local request_body
    request_body="$(_build_request_body "${cleaned_log}" "${build_url}")"

    _call_backend "${backend_url}" "${request_body}"

    if [[ "${AI_STATUS}" == "ok" ]]; then
        echo "AI analysis received from ${AI_PROVIDER} (${AI_MODEL})"
    fi

    export AI_ANALYSIS AI_PROVIDER AI_MODEL AI_STATUS
}

main
