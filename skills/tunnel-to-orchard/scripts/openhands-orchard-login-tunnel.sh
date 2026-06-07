#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage:
  openhands-orchard-login-tunnel [options]

Opens a local tunnel to a service running on Orchard's login node via Google
Cloud IAP:

  local machine -> orchard-login-001:127.0.0.1

Defaults are for an Agent Canvas backend already running on the Orchard login
node at 127.0.0.1:8000.

Options:
  --instance NAME           GCE instance/login node
                            default: orchard-login-001
  --project PROJECT         GCP project
                            default: cmu-gpu-cloud
  --zone ZONE               GCP zone
                            default: us-central1-c
  --local-bind ADDRESS      Local address for the tunnel listener
                            default: 127.0.0.1
  --local-port PORT         Local port to open
                            default: 8003
  --remote-host ADDRESS     Remote host from the login node's perspective
                            default: 127.0.0.1
  --remote-port PORT        Remote service port on the login node
                            default: 8000
  --api-check-path PATH     Authenticated API path to validate when a session
                            key is available
                            default: /api/conversations/search
  --health-path PATH        Health path to validate
                            default: /health
  --server-timeout SECONDS  Max time to wait for health
                            default: 120
  --no-health-check         Open the tunnel without validating health/API
  -h, --help                Show this help

Environment overrides:
  OH_ORCHARD_INSTANCE
  OH_ORCHARD_PROJECT
  OH_ORCHARD_ZONE
  OH_LOCAL_BIND
  OH_LOCAL_PORT
  OH_REMOTE_HOST
  OH_REMOTE_PORT
  OH_API_CHECK_PATH
  OH_HEALTH_PATH
  OH_SERVER_TIMEOUT
  OH_SESSION_API_KEYS_0
  LOCAL_BACKEND_API_KEY
  OH_SESSION_API_KEY_FILE
USAGE
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

log() {
  printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

INSTANCE=${OH_ORCHARD_INSTANCE:-orchard-login-001}
PROJECT=${OH_ORCHARD_PROJECT:-cmu-gpu-cloud}
ZONE=${OH_ORCHARD_ZONE:-us-central1-c}
LOCAL_BIND=${OH_LOCAL_BIND:-127.0.0.1}
LOCAL_PORT=${OH_LOCAL_PORT:-8003}
REMOTE_HOST=${OH_REMOTE_HOST:-127.0.0.1}
REMOTE_PORT=${OH_REMOTE_PORT:-8000}
API_CHECK_PATH=${OH_API_CHECK_PATH:-/api/conversations/search}
HEALTH_PATH=${OH_HEALTH_PATH:-/health}
SERVER_TIMEOUT=${OH_SERVER_TIMEOUT:-120}
HEALTH_CHECK=1
TUNNEL_PID=

while (($#)); do
  case "$1" in
    --instance)
      shift; (($#)) || die "--instance requires a value"; INSTANCE=$1
      ;;
    --project)
      shift; (($#)) || die "--project requires a value"; PROJECT=$1
      ;;
    --zone)
      shift; (($#)) || die "--zone requires a value"; ZONE=$1
      ;;
    --local-bind)
      shift; (($#)) || die "--local-bind requires a value"; LOCAL_BIND=$1
      ;;
    --local-port)
      shift; (($#)) || die "--local-port requires a value"; LOCAL_PORT=$1
      ;;
    --remote-host)
      shift; (($#)) || die "--remote-host requires a value"; REMOTE_HOST=$1
      ;;
    --remote-port)
      shift; (($#)) || die "--remote-port requires a value"; REMOTE_PORT=$1
      ;;
    --api-check-path)
      shift; (($#)) || die "--api-check-path requires a value"; API_CHECK_PATH=$1
      ;;
    --health-path)
      shift; (($#)) || die "--health-path requires a value"; HEALTH_PATH=$1
      ;;
    --server-timeout)
      shift; (($#)) || die "--server-timeout requires a value"; SERVER_TIMEOUT=$1
      ;;
    --no-health-check)
      HEALTH_CHECK=0
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
  shift
done

[[ $LOCAL_PORT =~ ^[0-9]+$ ]] || die "--local-port must be numeric"
[[ $REMOTE_PORT =~ ^[0-9]+$ ]] || die "--remote-port must be numeric"
[[ $SERVER_TIMEOUT =~ ^[0-9]+$ ]] || die "--server-timeout must be numeric"

require_cmd gcloud
require_cmd curl

if ! gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | grep -q .; then
  die "gcloud has no active account; run: gcloud auth login"
fi

SESSION_KEY_FILE=${OH_SESSION_API_KEY_FILE:-"$HOME/.openhands/agent-canvas/api-key.txt"}
SESSION_KEY=
if [[ -n ${LOCAL_BACKEND_API_KEY:-} ]]; then
  SESSION_KEY=$LOCAL_BACKEND_API_KEY
elif [[ -n ${OH_SESSION_API_KEYS_0:-} ]]; then
  SESSION_KEY=$OH_SESSION_API_KEYS_0
elif [[ -s $SESSION_KEY_FILE ]]; then
  SESSION_KEY=$(tr -d '\r\n' <"$SESSION_KEY_FILE")
fi

cleanup() {
  local status=$?
  trap - EXIT INT TERM
  if [[ -n ${TUNNEL_PID:-} ]] && kill -0 "$TUNNEL_PID" >/dev/null 2>&1; then
    log "closing gcloud IAP tunnel"
    kill "$TUNNEL_PID" >/dev/null 2>&1 || true
    wait "$TUNNEL_PID" >/dev/null 2>&1 || true
  fi
  exit "$status"
}

trap cleanup EXIT INT TERM

curl_host=$LOCAL_BIND
case "$curl_host" in
  0.0.0.0|::) curl_host=127.0.0.1 ;;
esac
LOCAL_URL="http://${curl_host}:${LOCAL_PORT}"

log "opening tunnel: ${LOCAL_BIND}:${LOCAL_PORT} -> ${INSTANCE}:${REMOTE_HOST}:${REMOTE_PORT} via Google IAP"
gcloud compute ssh "$INSTANCE" \
  --zone "$ZONE" \
  --project "$PROJECT" \
  --tunnel-through-iap \
  -- \
  -N \
  -L "${LOCAL_BIND}:${LOCAL_PORT}:${REMOTE_HOST}:${REMOTE_PORT}" \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 &
TUNNEL_PID=$!

sleep 2
if ! kill -0 "$TUNNEL_PID" >/dev/null 2>&1; then
  wait "$TUNNEL_PID" || true
  die "gcloud IAP tunnel failed to start"
fi

if [[ $HEALTH_CHECK -eq 1 ]]; then
  log "waiting for health at ${LOCAL_URL}${HEALTH_PATH}"
  deadline=$((SECONDS + SERVER_TIMEOUT))
  until curl -fsS --max-time 2 "${LOCAL_URL}${HEALTH_PATH}" >/dev/null 2>&1; do
    if ! kill -0 "$TUNNEL_PID" >/dev/null 2>&1; then
      wait "$TUNNEL_PID" || true
      die "gcloud IAP tunnel exited before the service became healthy"
    fi
    if ((SECONDS >= deadline)); then
      die "timed out waiting for ${LOCAL_URL}${HEALTH_PATH}; is the remote service running on ${REMOTE_HOST}:${REMOTE_PORT}?"
    fi
    sleep 2
  done

  if [[ -n $SESSION_KEY ]]; then
    status=$(curl -sS -L --max-time 5 -o /dev/null -w '%{http_code}' \
      -H "X-Session-API-Key: $SESSION_KEY" \
      "${LOCAL_URL}${API_CHECK_PATH}" || true)
    case "$status" in
      2*|3*) log "authenticated API reachable at ${LOCAL_URL}${API_CHECK_PATH}" ;;
      *) die "authenticated API check failed at ${LOCAL_URL}${API_CHECK_PATH}; HTTP status: ${status:-none}" ;;
    esac
  else
    log "no Agent Canvas session key found; skipped authenticated API check"
  fi
fi

local_state_root=${XDG_RUNTIME_DIR:-$HOME/.cache}/openhands-orchard-tunnel
mkdir -p "$local_state_root"
chmod 700 "$local_state_root"
LOCAL_ENV_FILE="$local_state_root/orchard-login-${LOCAL_PORT}.env"
{
  printf 'OPENHANDS_AGENT_SERVER_URL=%q\n' "$LOCAL_URL"
  printf 'AGENT_CANVAS_INGRESS_URL=%q\n' "$LOCAL_URL"
  printf 'OPENHANDS_AUTOMATION_API_URL=%q\n' "${LOCAL_URL}/api/automation"
  if [[ -n $SESSION_KEY ]]; then
    printf 'OPENHANDS_AUTOMATION_API_KEY=%q\n' "$SESSION_KEY"
    printf 'OH_SESSION_API_KEYS_0=%q\n' "$SESSION_KEY"
  fi
  printf 'OH_SESSION_API_KEY_FILE=%q\n' "$SESSION_KEY_FILE"
  printf 'ORCHARD_INSTANCE=%q\n' "$INSTANCE"
  printf 'ORCHARD_PROJECT=%q\n' "$PROJECT"
  printf 'ORCHARD_ZONE=%q\n' "$ZONE"
} >"$LOCAL_ENV_FILE"
chmod 600 "$LOCAL_ENV_FILE"

printf '\n'
printf 'Orchard login-node tunnel is open.\n'
printf '  Ingress URL: %s\n' "$LOCAL_URL"
printf '  Automation API: %s/api/automation\n' "$LOCAL_URL"
printf '  Env file: %s\n' "$LOCAL_ENV_FILE"
printf '\n'
printf 'Press Ctrl-C to close the tunnel.\n'

wait "$TUNNEL_PID"
