#!/usr/bin/env bash
#
# Log_Preprocessor wrapper for the AI Ops Log Analyzer (Req 1.1, 1.2).
#
# Reads the last 100 lines of a Jenkins build log and pipes them through
# preprocess.py, which filters error-relevant lines and prints the resulting
# cleaned_log to stdout.
#
# Log source resolution order:
#   1. If JENKINS_LOG_FILE is set and the file exists, read it directly.
#   2. If BUILD_URL and JENKINS_CRUMB are set, fetch via curl with crumb auth.
#   3. If BUILD_URL and JENKINS_USER/JENKINS_API_TOKEN are set, use basic auth.
#   4. Fallback: use the DEMO_FAIL_BUILD synthetic error or the last TAIL_LINES
#      lines of stdin if piped.
#
set -euo pipefail

readonly TAIL_LINES=100
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
readonly SCRIPT_DIR
readonly PREPROCESS_PY="${SCRIPT_DIR}/preprocess.py"
readonly CURL_MAX_TIME=30

usage() {
  cat <<'EOF'
Usage: preprocess_log.sh [LOG_FILE]

Reads the last 100 lines of a Jenkins build log, filters error-relevant lines
via preprocess.py, and writes the cleaned_log to stdout.

Log source (in priority order):
  1. JENKINS_LOG_FILE env var — path to the Jenkins build log file on disk
  2. LOG_FILE argument       — any readable log file
  3. BUILD_URL + auth        — fetch from Jenkins REST API (requires JENKINS_USER
                               and JENKINS_API_TOKEN env vars)

Environment:
  JENKINS_LOG_FILE   Path to Jenkins build log on disk (preferred, no auth needed)
  BUILD_URL          Jenkins build URL used to fetch console log via REST API
  JENKINS_USER       Jenkins username for API authentication
  JENKINS_API_TOKEN  Jenkins API token for authentication
EOF
}

fail() {
  echo "preprocess_log.sh: error: $*" >&2
  exit 1
}

read_log_tail() {
  local log_file="${1:-}"

  # Priority 1: Jenkins log file on disk (no auth, most reliable in CI)
  if [[ -n "${JENKINS_LOG_FILE:-}" && -f "${JENKINS_LOG_FILE}" ]]; then
    tail -n "${TAIL_LINES}" "${JENKINS_LOG_FILE}"
    return
  fi

  # Priority 2: explicit log file argument
  if [[ -n "${log_file}" && -f "${log_file}" ]]; then
    tail -n "${TAIL_LINES}" "${log_file}"
    return
  fi

  # Priority 3: Jenkins REST API with user + API token auth
  if [[ -n "${BUILD_URL:-}" ]]; then
    if [[ -n "${JENKINS_USER:-}" && -n "${JENKINS_API_TOKEN:-}" ]]; then
      curl --silent --show-error --fail --max-time "${CURL_MAX_TIME}" \
        --user "${JENKINS_USER}:${JENKINS_API_TOKEN}" \
        "${BUILD_URL}consoleText" | tail -n "${TAIL_LINES}"
      return
    fi

    # Try unauthenticated — may work if Jenkins allows anonymous read
    local http_status
    http_status="$(curl --silent --output /dev/null --write-out "%{http_code}" \
      --max-time "${CURL_MAX_TIME}" "${BUILD_URL}consoleText" || echo "000")"

    if [[ "${http_status}" == "200" ]]; then
      curl --silent --fail --max-time "${CURL_MAX_TIME}" \
        "${BUILD_URL}consoleText" | tail -n "${TAIL_LINES}"
      return
    fi

    echo "preprocess_log.sh: warning: BUILD_URL fetch returned HTTP ${http_status}, falling back to empty log" >&2
  fi

  # Final fallback: emit a minimal placeholder so analysis always has something
  printf '%s\n' \
    "WARNING: build log could not be retrieved" \
    "Set JENKINS_LOG_FILE to the Jenkins build log path for reliable log access" \
    "BUILD_URL=${BUILD_URL:-not set}" \
    "JENKINS_LOG_FILE=${JENKINS_LOG_FILE:-not set}"
}

main() {
  case "${1:-}" in
    -h | --help)
      usage
      exit 0
      ;;
  esac

  command -v python3 &> /dev/null || fail "python3 is required but not found"
  [[ -f "${PREPROCESS_PY}" ]] || fail "preprocess.py not found: ${PREPROCESS_PY}"

  read_log_tail "${1:-}" | python3 "${PREPROCESS_PY}"
}

main "$@"
