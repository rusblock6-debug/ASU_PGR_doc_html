#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

SETTINGS_COMPOSE_FILE="docker-compose.settings-bort.yaml"
BASE_ENV_FILE=""
SETTINGS_SERVICE="settings-service"
INIT_URL_TEMPLATE="http://127.0.0.1:8017/api/secrets/init/%s"
EXPORT_ENV_URL="http://127.0.0.1:8017/api/admin/export-env"
OUTPUT_ENV_FILE=".env.settings.generated"
POLL_INTERVAL_SEC=2
MAX_WAIT_SEC=300
SKIP_INIT=0
VEHICLE_ID_OVERRIDE="${VEHICLE_ID:-}"

USE_BASE_ENV=0
BASE_ENV_ARGS=()
OUTPUT_ENV_PATH=""
OUTPUT_ENV_CONTAINER_PATH=""
DOCKER_COMPOSE_CMD=()

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

fail() {
  printf '[%s] ERROR: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2
  exit 1
}

usage() {
  cat <<'USAGE'
Usage:
  scripts/bootstrap_with_settings.sh [options]

Options:
  --settings-compose-file <path> Compose file for settings stage (default: docker-compose.settings-bort.yaml)
  --base-env-file <path>         Optional base env file
  --settings-service <name>      Settings service name in settings compose (default: settings-service)
  --init-url-template <tpl>      Optional init URL template with one %s for vehicle_id
                                 (default: http://127.0.0.1:8017/api/secrets/init/%s)
  --export-env-url <url>         Endpoint that exports env file from settings-bort
                                 (default: http://127.0.0.1:8017/api/admin/export-env)
  --output-env-file <path>       Expected generated env file (default: .env.settings.generated)
  --vehicle-id <id>              Vehicle ID to use for init call (overrides env-file value)
  --poll-interval <sec>          Poll interval in seconds (default: 2)
  --max-wait <sec>               Timeout in seconds (default: 300)
  --compose-file <path>          Deprecated: ignored, kept for compatibility
  --pull-policy <policy>         Deprecated: ignored, kept for compatibility
  --skip-init                    Do not call init endpoint before waiting
  --skip-full-stack              Deprecated: ignored, kept for compatibility
  -h, --help                     Show help
USAGE
}

require_cmd() {
  local cmd="$1"
  command -v "${cmd}" >/dev/null 2>&1 || fail "Required command not found: ${cmd}"
}

resolve_docker_compose_cmd() {
  if command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD=(docker-compose)
  else
    DOCKER_COMPOSE_CMD=(docker compose)
  fi
}

require_option_value() {
  local opt="$1"
  local next="${2:-}"
  if [[ -z "${next}" || "${next}" == --* ]]; then
    fail "Option ${opt} requires a value"
  fi
}

validate_uint() {
  local name="$1"
  local value="$2"
  local min="${3:-0}"
  if [[ ! "${value}" =~ ^[0-9]+$ ]]; then
    fail "${name} must be an integer, got: ${value}"
  fi
  if (( value < min )); then
    fail "${name} must be >= ${min}, got: ${value}"
  fi
}

read_env_value() {
  local env_file="$1"
  local key="$2"
  local line

  line="$(grep -E "^${key}=" "${env_file}" | tail -n 1 || true)"
  [[ -n "${line}" ]] || return 1

  local value="${line#*=}"
  value="$(printf '%s' "${value}" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
  value="${value%\"}"
  value="${value#\"}"
  value="${value%\'}"
  value="${value#\'}"
  printf '%s' "${value}"
}

ensure_exported_env() {
  local env_file="$1"
  [[ -f "${env_file}" ]] || return 1
  grep -Eq '^[A-Za-z_][A-Za-z0-9_]*=' "${env_file}"
}

resolve_base_env_usage() {
  if [[ -n "${BASE_ENV_FILE}" && -f "${BASE_ENV_FILE}" ]]; then
    USE_BASE_ENV=1
    BASE_ENV_ARGS=(--env-file "${BASE_ENV_FILE}")
    return
  fi
  if [[ -n "${BASE_ENV_FILE}" ]]; then
    log "Base env file not found: ${BASE_ENV_FILE}. Continue without base env."
  fi
}

resolve_output_paths() {
  if [[ "${OUTPUT_ENV_FILE}" = /* ]]; then
    OUTPUT_ENV_PATH="${OUTPUT_ENV_FILE}"
    if [[ "${OUTPUT_ENV_PATH}" == "${PROJECT_ROOT}"/* ]]; then
      local relative_path="${OUTPUT_ENV_PATH#${PROJECT_ROOT}/}"
      OUTPUT_ENV_CONTAINER_PATH="/workspace/dispatching/${relative_path}"
    else
      OUTPUT_ENV_CONTAINER_PATH="${OUTPUT_ENV_PATH}"
      log "Output env path is outside project root, container path may be unreachable: ${OUTPUT_ENV_CONTAINER_PATH}"
    fi
    return
  fi

  local relative_path="${OUTPUT_ENV_FILE#./}"
  OUTPUT_ENV_PATH="${PROJECT_ROOT}/${relative_path}"
  OUTPUT_ENV_CONTAINER_PATH="/workspace/dispatching/${relative_path}"
}

resolve_vehicle_id() {
  local vehicle_id="${VEHICLE_ID_OVERRIDE:-}"
  if [[ -z "${vehicle_id}" && "${USE_BASE_ENV}" -eq 1 ]]; then
    vehicle_id="$(read_env_value "${BASE_ENV_FILE}" "VEHICLE_ID" || true)"
  fi
  printf '%s' "${vehicle_id}"
}

start_settings_service() {
  local cmd=(
    "${DOCKER_COMPOSE_CMD[@]}"
    -f "${SETTINGS_COMPOSE_FILE}"
    "${BASE_ENV_ARGS[@]}"
  )

  log "Starting ${SETTINGS_SERVICE} from ${SETTINGS_COMPOSE_FILE}"
  log "settings-bort export path (container): ${OUTPUT_ENV_CONTAINER_PATH}"
  BORT_ENV_OUTPUT_PATH="${OUTPUT_ENV_CONTAINER_PATH}" "${cmd[@]}" up -d --build "${SETTINGS_SERVICE}"
}

maybe_call_init() {
  if [[ "${SKIP_INIT}" -eq 1 ]]; then
    log "--skip-init enabled, waiting for manual init via UI/curl"
    return
  fi

  local vehicle_id
  vehicle_id="$(resolve_vehicle_id)"
  if [[ -z "${vehicle_id}" ]]; then
    log "VEHICLE_ID is not set, skipping auto init (manual init via UI/curl is expected)"
    return
  fi

  local init_url
  init_url="$(printf "${INIT_URL_TEMPLATE}" "${vehicle_id}")"
  log "Calling init for VEHICLE_ID=${vehicle_id}: ${init_url}"
  curl -fsS -X POST "${init_url}" >/dev/null || log "Init request failed, continue waiting for manual init"
}

wait_for_exported_env() {
  local deadline=$((SECONDS + MAX_WAIT_SEC))
  local ready=0

  log "Waiting for generated env file on host: ${OUTPUT_ENV_PATH}"
  while (( SECONDS < deadline )); do
    curl -fsS -X POST "${EXPORT_ENV_URL}" >/dev/null 2>&1 || true
    if ensure_exported_env "${OUTPUT_ENV_PATH}"; then
      ready=1
      break
    fi
    sleep "${POLL_INTERVAL_SEC}"
  done

  if [[ "${ready}" -ne 1 ]]; then
    fail "Timed out after ${MAX_WAIT_SEC}s waiting for generated env file: ${OUTPUT_ENV_PATH}"
  fi
  log "Generated env file is ready: ${OUTPUT_ENV_PATH}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose-file)
      require_option_value "$1" "${2:-}"
      shift 2
      ;;
    --settings-compose-file)
      require_option_value "$1" "${2:-}"
      SETTINGS_COMPOSE_FILE="$2"
      shift 2
      ;;
    --base-env-file)
      require_option_value "$1" "${2:-}"
      BASE_ENV_FILE="$2"
      shift 2
      ;;
    --settings-service)
      require_option_value "$1" "${2:-}"
      SETTINGS_SERVICE="$2"
      shift 2
      ;;
    --init-url-template)
      require_option_value "$1" "${2:-}"
      INIT_URL_TEMPLATE="$2"
      shift 2
      ;;
    --export-env-url)
      require_option_value "$1" "${2:-}"
      EXPORT_ENV_URL="$2"
      shift 2
      ;;
    --output-env-file)
      require_option_value "$1" "${2:-}"
      OUTPUT_ENV_FILE="$2"
      shift 2
      ;;
    --vehicle-id)
      require_option_value "$1" "${2:-}"
      VEHICLE_ID_OVERRIDE="$2"
      shift 2
      ;;
    --poll-interval)
      require_option_value "$1" "${2:-}"
      POLL_INTERVAL_SEC="$2"
      shift 2
      ;;
    --max-wait)
      require_option_value "$1" "${2:-}"
      MAX_WAIT_SEC="$2"
      shift 2
      ;;
    --pull-policy)
      require_option_value "$1" "${2:-}"
      shift 2
      ;;
    --skip-init)
      SKIP_INIT=1
      shift
      ;;
    --skip-full-stack)
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1"
      ;;
  esac
done

[[ -f "${SETTINGS_COMPOSE_FILE}" ]] || fail "Settings compose file not found: ${SETTINGS_COMPOSE_FILE}"

require_cmd docker
require_cmd curl
resolve_docker_compose_cmd
validate_uint "POLL_INTERVAL_SEC" "${POLL_INTERVAL_SEC}" 1
validate_uint "MAX_WAIT_SEC" "${MAX_WAIT_SEC}" 1

resolve_base_env_usage
resolve_output_paths

start_settings_service
maybe_call_init
wait_for_exported_env

log "Bootstrap completed successfully"
