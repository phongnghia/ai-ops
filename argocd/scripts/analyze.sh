#!/usr/bin/env bash
# analyze.sh — Request AI analysis from the backend for an ArgoCD sync failure.
#
# Called by the ArgoCD Notifications webhook handler when an Application
# transitions to a degraded or error state. Sends the failure context to
# POST /api/analyze-log and exports the result for notify.py to display.
#
# ArgoCD Notifications populates the following environment variables before
# calling this script (configured in argocd-notifications-cm.yaml):
#
#   ARGOCD_APP_NAME          Application name (e.g. my-service)
#   ARGOCD_APP_NAMESPACE     Namespace where the app is deployed
#   ARGOCD_APP_SYNC_STATUS   Current sync status (e.g. OutOfSync, Unknown)
#   ARGOCD_APP_HEALTH_STATUS Current health status (e.g. Degraded, Missing)
#   ARGOCD_APP_CONDITIONS    Comma-separated list of error conditions
#   ARGOCD_APP_SERVER        Cluster API server URL
#   AI_OPS_BACKEND_URL       Backend service URL (from argocd-notifications-secret)
#
# Exported after execution:
#   AI_ANALYSIS   Full analysis text returned by the backend
#   AI_PROVIDER   LLM provider that served the request
#   AI_MODEL      Concrete model used
#   AI_STATUS     "ok" on HTTP 200, "failed" otherwise
#
set -euo pipefail

readonly ANALYZE_ENDPOINT="/api/analyze-log"
readonly CURL_TIMEOUT_SECONDS=300

AI_ANALYSIS=""
AI_PROVIDER="unknown"
AI_MODEL="unknown"
AI_STATUS="failed"

_resolve_backend_url() {
    echo "${AI_OPS_BACKEND_URL:-http://localhost:8000}"
}

_build_cleaned_log() {
    # Assemble a structured log from ArgoCD context variables.
    # ArgoCD does not provide raw container logs via notifications, so we
    # build a diagnostic summary from the available metadata fields.
    local app="${ARGOCD_APP_NAME:-unknown-app}"
    local namespace="${ARGOCD_APP_NAMESPACE:-unknown}"
    local sync_status="${ARGOCD_APP_SYNC_STATUS:-Unknown}"
    local health_status="${ARGOCD_APP_HEALTH_STATUS:-Unknown}"
    local conditions="${ARGOCD_APP_CONDITIONS:-No conditions reported}"
    local server="${ARGOCD_APP_SERVER:-unknown-cluster}"

    printf '%s\n' \
        "ArgoCD Application Failure Report" \
        "Application: ${app}" \
        "Namespace:   ${namespace}" \
        "Cluster:     ${server}" \
        "" \
        "ERROR: Sync status: ${sync_status}" \
        "ERROR: Health status: ${health_status}" \
        "" \
        "Conditions:" \
        "${conditions}"
}

_build_request_body() {
    local cleaned_log="${1}"
    local app_name="${ARGOCD_APP_NAME:-unknown-app}"

    APP_NAME_VALUE="${app_name}" \
    CLEANED_LOG_VALUE="${cleaned_log}" \
    AI_OPS_BACKEND_URL_VALUE="${AI_OPS_BACKEND_URL:-http://localhost:8000}" \
    python3 -c '
import json, os
app = os.environ["APP_NAME_VALUE"]
backend = os.environ["AI_OPS_BACKEND_URL_VALUE"]
print(json.dumps({
    "build_number": app,
    "job_name":     f"argocd/{app}",
    "build_url":    f"{backend.rstrip(\"/\")}/applications/{app}",
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
            --header "X-AI-Client: ArgoCD" \
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

    echo "AI analysis backend: ${backend_url}"
    echo "Application: ${ARGOCD_APP_NAME:-unknown}"

    command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }
    command -v curl    >/dev/null || { echo "curl is required"    >&2; exit 1; }

    local cleaned_log
    cleaned_log="$(_build_cleaned_log)"

    local request_body
    request_body="$(_build_request_body "${cleaned_log}")"

    _call_backend "${backend_url}" "${request_body}"

    if [[ "${AI_STATUS}" == "ok" ]]; then
        echo "AI analysis received from ${AI_PROVIDER} (${AI_MODEL})"
    fi

    export AI_ANALYSIS AI_PROVIDER AI_MODEL AI_STATUS
}

main
