#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage:
  openhands-slurm-tunnel [options]

Starts an authenticated Agent Canvas backend stack in a Slurm job on Babel,
waits for the allocated compute node, and opens a local tunnel:

  local machine -> login jump host -> allocated compute node:127.0.0.1

By default, the script assumes the checkout is available on Babel at:

  ~/homework

If that directory is not itself the checkout but contains `agent-canvas/`, the
script uses that subdirectory automatically. If you run this script from an
Agent Canvas checkout whose path also exists on Babel, that path may be used as
the remote repo path. macOS-local paths such as `/Users/...` are not sent to
Babel as defaults because they are not valid on the login/compute filesystem.

Options:
  --login USER@HOST          SSH login jump host
                             default: gneubig@login4.babel.cs.cmu.edu
  --remote-repo DIR          agent-canvas checkout on the login/compute filesystem
                             default: ~/homework, with automatic
                             ~/homework/agent-canvas fallback
  --remote-ref REF           Git ref to check out before starting
                             default: unset; use the existing checkout
  --local-bind ADDRESS       Local address for the tunnel listener
                             default: 127.0.0.1
  --local-port PORT          Local port to open
                             default: 8002
  --server-port PORT         Ingress port used by the backend stack on the compute node
                             default: 8000
  --compute-user USER        SSH username for the compute node
                             default: user from --login
  --job-name NAME            Slurm job name
                             default: agent-canvas-backend
  --time TIME                Slurm time limit, e.g. 04:00:00
  --partition PARTITION      Slurm partition
  --account ACCOUNT          Slurm account
  --qos QOS                  Slurm QOS
  --gres GRES                Slurm generic resources
                             default: gpu:1 (set OH_SLURM_GRES= to disable)
  --constraint CONSTRAINT    Slurm node constraint
  --cpus-per-task N          Slurm CPUs per task
  --mem MEM                  Slurm memory, e.g. 16G
  --sbatch-arg ARG           Additional raw sbatch argument; may be repeated
  --setup-cmd CMD            Optional command run before starting the server
  --start-cmd CMD            Override the server start command
  --queue-timeout SECONDS    Max time to wait for a node allocation
                             default: 900
  --server-timeout SECONDS   Max time to wait for /health through the tunnel
                             default: 240
  --poll-interval SECONDS    Slurm polling interval
                             default: 3
  --keep-job                 Do not scancel the Slurm job when this exits
  -h, --help                 Show this help

Environment overrides:
  OH_BABEL_LOGIN
  OH_AGENT_CANVAS_REPO_DIR
  OH_REMOTE_REPO_DIR
  OH_LOCAL_BIND
  OH_LOCAL_PORT
  OH_SERVER_PORT
  OH_ALLOW_CORS_ORIGINS
  OH_SLURM_JOB_NAME
  OH_SLURM_GRES
  OH_REMOTE_GIT_REF
  OH_REMOTE_SETUP_CMD
  OH_REMOTE_START_CMD
  OH_NODE_BIN
  OH_SECRET_KEY
  OH_SECRET_KEY_DOTENV
  OH_SECRET_KEY_FILE

The default start command is:

  agent-canvas --backend-only --port "$OH_AGENT_SERVER_PORT"

The job puts an `agent-canvas` wrapper from the selected checkout first on PATH,
so this resolves to the checkout passed via `--remote-repo` rather than a
globally installed package. If `--remote-ref` is provided, the script first
fetches that ref and runs it from an isolated detached worktree.
USAGE
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

log() {
  printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2
}

quote() {
  printf '%q' "$1"
}

quote_words() {
  local word out=""
  for word in "$@"; do
    out+=" $(quote "$word")"
  done
  printf '%s' "${out# }"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

parse_kv() {
  local content=$1 key value
  while IFS='=' read -r key value; do
    case "$key" in
      JOB_ID) JOB_ID=$value ;;
      STATE_DIR) REMOTE_STATE_DIR=$value ;;
      JOB_SCRIPT) REMOTE_JOB_SCRIPT=$value ;;
      SOURCE) SNAPSHOT_SOURCE=$value ;;
      STATE) SNAPSHOT_STATE=$value ;;
      NODES) SNAPSHOT_NODES=$value ;;
      REASON) SNAPSHOT_REASON=$value ;;
      NODE) SNAPSHOT_NODE=$value ;;
    esac
  done <<<"$content"
}

LOGIN=${OH_BABEL_LOGIN:-gneubig@login4.babel.cs.cmu.edu}
if [[ ${OH_AGENT_CANVAS_REPO_DIR+x} ]]; then
  REMOTE_REPO_DIR=$OH_AGENT_CANVAS_REPO_DIR
  REMOTE_REPO_DIR_EXPLICIT=1
elif [[ ${OH_REMOTE_REPO_DIR+x} ]]; then
  REMOTE_REPO_DIR=$OH_REMOTE_REPO_DIR
  REMOTE_REPO_DIR_EXPLICIT=1
else
  REMOTE_REPO_DIR='~/homework'
  REMOTE_REPO_DIR_EXPLICIT=0
  if [[ -f package.json && -f bin/agent-canvas.mjs && $PWD != /Users/* ]]; then
    REMOTE_REPO_DIR=$PWD
  fi
fi
LOCAL_BIND=${OH_LOCAL_BIND:-127.0.0.1}
LOCAL_PORT=${OH_LOCAL_PORT:-8002}
SERVER_HOST=127.0.0.1
SERVER_PORT=${OH_SERVER_PORT:-8000}
ALLOW_CORS_ORIGINS=${OH_ALLOW_CORS_ORIGINS:-'["http://localhost:3001","http://localhost:8001"]'}
AUTOMATION_CORS_ORIGINS=${OH_AUTOMATION_CORS_ORIGINS:-'*'}
COMPUTE_USER=${OH_COMPUTE_USER:-}
JOB_NAME=${OH_SLURM_JOB_NAME:-agent-canvas-backend}
REMOTE_STATE_ROOT=${OH_REMOTE_STATE_ROOT:-'~/.cache/openhands-slurm-tunnel'}
REMOTE_GIT_REF=${OH_REMOTE_GIT_REF-}
SETUP_CMD=${OH_REMOTE_SETUP_CMD:-}
START_CMD=${OH_REMOTE_START_CMD:-'agent-canvas --backend-only --port "$OH_AGENT_SERVER_PORT"'}
NODE_BIN=${OH_NODE_BIN:-}
DEFAULT_GRES=${OH_SLURM_GRES-gpu:1}
QUEUE_TIMEOUT=900
SERVER_TIMEOUT=240
POLL_INTERVAL=3
KEEP_JOB=0

SBATCH_ARGS=()
SBATCH_GRES_EXPLICIT=0
SSH_OPTS=(-T -o StrictHostKeyChecking=accept-new -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3)

while (($#)); do
  case "$1" in
    --login)
      shift; (($#)) || die "--login requires a value"; LOGIN=$1
      ;;
    --remote-repo)
      shift; (($#)) || die "--remote-repo requires a value"; REMOTE_REPO_DIR=$1; REMOTE_REPO_DIR_EXPLICIT=1
      ;;
    --remote-ref)
      shift; (($#)) || die "--remote-ref requires a value"; REMOTE_GIT_REF=$1
      ;;
    --local-bind)
      shift; (($#)) || die "--local-bind requires a value"; LOCAL_BIND=$1
      ;;
    --local-port)
      shift; (($#)) || die "--local-port requires a value"; LOCAL_PORT=$1
      ;;
    --server-port)
      shift; (($#)) || die "--server-port requires a value"; SERVER_PORT=$1
      ;;
    --compute-user)
      shift; (($#)) || die "--compute-user requires a value"; COMPUTE_USER=$1
      ;;
    --job-name)
      shift; (($#)) || die "--job-name requires a value"; JOB_NAME=$1
      ;;
    --time)
      shift; (($#)) || die "--time requires a value"; SBATCH_ARGS+=("--time=$1")
      ;;
    --partition)
      shift; (($#)) || die "--partition requires a value"; SBATCH_ARGS+=("--partition=$1")
      ;;
    --account)
      shift; (($#)) || die "--account requires a value"; SBATCH_ARGS+=("--account=$1")
      ;;
    --qos)
      shift; (($#)) || die "--qos requires a value"; SBATCH_ARGS+=("--qos=$1")
      ;;
    --gres)
      shift; (($#)) || die "--gres requires a value"; SBATCH_ARGS+=("--gres=$1"); SBATCH_GRES_EXPLICIT=1
      ;;
    --constraint)
      shift; (($#)) || die "--constraint requires a value"; SBATCH_ARGS+=("--constraint=$1")
      ;;
    --cpus-per-task)
      shift; (($#)) || die "--cpus-per-task requires a value"; SBATCH_ARGS+=("--cpus-per-task=$1")
      ;;
    --mem)
      shift; (($#)) || die "--mem requires a value"; SBATCH_ARGS+=("--mem=$1")
      ;;
    --sbatch-arg)
      shift; (($#)) || die "--sbatch-arg requires a value"; SBATCH_ARGS+=("$1")
      case "$1" in
        --gres|--gres=*|--gpus|--gpus=*) SBATCH_GRES_EXPLICIT=1 ;;
      esac
      ;;
    --setup-cmd)
      shift; (($#)) || die "--setup-cmd requires a value"; SETUP_CMD=$1
      ;;
    --start-cmd)
      shift; (($#)) || die "--start-cmd requires a value"; START_CMD=$1
      ;;
    --queue-timeout)
      shift; (($#)) || die "--queue-timeout requires a value"; QUEUE_TIMEOUT=$1
      ;;
    --server-timeout)
      shift; (($#)) || die "--server-timeout requires a value"; SERVER_TIMEOUT=$1
      ;;
    --poll-interval)
      shift; (($#)) || die "--poll-interval requires a value"; POLL_INTERVAL=$1
      ;;
    --keep-job)
      KEEP_JOB=1
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
[[ $SERVER_PORT =~ ^[0-9]+$ ]] || die "--server-port must be numeric"
[[ $QUEUE_TIMEOUT =~ ^[0-9]+$ ]] || die "--queue-timeout must be numeric"
[[ $SERVER_TIMEOUT =~ ^[0-9]+$ ]] || die "--server-timeout must be numeric"
[[ $POLL_INTERVAL =~ ^[0-9]+$ ]] || die "--poll-interval must be numeric"
[[ $POLL_INTERVAL -gt 0 ]] || die "--poll-interval must be greater than zero"

if [[ $SBATCH_GRES_EXPLICIT -eq 0 && -n $DEFAULT_GRES ]]; then
  if ((${#SBATCH_ARGS[@]})); then
    SBATCH_ARGS=("--gres=$DEFAULT_GRES" "${SBATCH_ARGS[@]}")
  else
    SBATCH_ARGS=("--gres=$DEFAULT_GRES")
  fi
fi

require_cmd ssh
require_cmd curl
require_cmd openssl

if [[ -z ${OH_SECRET_KEY:-} ]]; then
  DOTENV_SECRET_FILE=${OH_SECRET_KEY_DOTENV:-}
  if [[ -z $DOTENV_SECRET_FILE && -f "$PWD/.env" && -f "$PWD/package.json" && -f "$PWD/bin/agent-canvas.mjs" ]]; then
    DOTENV_SECRET_FILE="$PWD/.env"
  fi
  if [[ -z $DOTENV_SECRET_FILE && -f "$HOME/work/agent-canvas/.env" ]]; then
    DOTENV_SECRET_FILE="$HOME/work/agent-canvas/.env"
  fi
  if [[ -n $DOTENV_SECRET_FILE && -f $DOTENV_SECRET_FILE ]]; then
    DOTENV_SECRET=$(
      set +u
      set -a
      source "$DOTENV_SECRET_FILE" >/dev/null 2>&1 || exit 0
      printf '%s' "${OH_SECRET_KEY:-}"
    )
    if [[ -n $DOTENV_SECRET ]]; then
      OH_SECRET_KEY=$DOTENV_SECRET
      log "OH_SECRET_KEY not set; loaded from $DOTENV_SECRET_FILE"
    fi
  fi
fi

SECRET_KEY_FILE=${OH_SECRET_KEY_FILE:-"$HOME/.openhands/agent-canvas/secret-key.txt"}
secret_key_dir=${SECRET_KEY_FILE%/*}
if [[ $secret_key_dir != "$SECRET_KEY_FILE" ]]; then
  mkdir -p "$secret_key_dir"
  chmod 700 "$secret_key_dir"
fi

if [[ -n ${OH_SECRET_KEY:-} ]]; then
  SECRET_KEY=$OH_SECRET_KEY
  printf '%s\n' "$SECRET_KEY" >"$SECRET_KEY_FILE"
  chmod 600 "$SECRET_KEY_FILE"
else
  if [[ -s $SECRET_KEY_FILE ]]; then
    SECRET_KEY=$(<"$SECRET_KEY_FILE")
  else
    SECRET_KEY=$(openssl rand -hex 32)
    printf '%s\n' "$SECRET_KEY" >"$SECRET_KEY_FILE"
    chmod 600 "$SECRET_KEY_FILE"
  fi
  log "OH_SECRET_KEY not set; using local secret file $SECRET_KEY_FILE"
fi

SESSION_KEY_FILE=${OH_SESSION_API_KEY_FILE:-"$HOME/.openhands/agent-canvas/api-key.txt"}
session_key_dir=${SESSION_KEY_FILE%/*}
if [[ $session_key_dir != "$SESSION_KEY_FILE" ]]; then
  mkdir -p "$session_key_dir"
  chmod 700 "$session_key_dir"
fi
if [[ -n ${LOCAL_BACKEND_API_KEY:-} ]]; then
  SESSION_KEY=$LOCAL_BACKEND_API_KEY
  printf '%s\n' "$SESSION_KEY" >"$SESSION_KEY_FILE"
  chmod 600 "$SESSION_KEY_FILE"
elif [[ -n ${OH_SESSION_API_KEYS_0:-} ]]; then
  SESSION_KEY=$OH_SESSION_API_KEYS_0
  printf '%s\n' "$SESSION_KEY" >"$SESSION_KEY_FILE"
  chmod 600 "$SESSION_KEY_FILE"
elif [[ -s $SESSION_KEY_FILE ]]; then
  SESSION_KEY=$(tr -d '\r\n' <"$SESSION_KEY_FILE")
else
  SESSION_KEY=$(openssl rand -hex 32)
  printf '%s\n' "$SESSION_KEY" >"$SESSION_KEY_FILE"
  chmod 600 "$SESSION_KEY_FILE"
fi
JOB_ID=
REMOTE_STATE_DIR=
REMOTE_JOB_SCRIPT=
COMPUTE_NODE=
TUNNEL_PID=
LOCAL_ENV_FILE=

cleanup() {
  local status=$?
  trap - EXIT INT TERM

  if [[ -n ${TUNNEL_PID:-} ]] && kill -0 "$TUNNEL_PID" >/dev/null 2>&1; then
    log "closing SSH tunnel"
    kill "$TUNNEL_PID" >/dev/null 2>&1 || true
    wait "$TUNNEL_PID" >/dev/null 2>&1 || true
  fi

  if [[ -n ${JOB_ID:-} && $KEEP_JOB -eq 0 ]]; then
    log "cancelling Slurm job $JOB_ID"
    ssh "${SSH_OPTS[@]}" "$LOGIN" "scancel $(quote "$JOB_ID")" >/dev/null 2>&1 || true
  elif [[ -n ${JOB_ID:-} && $KEEP_JOB -eq 1 ]]; then
    log "leaving Slurm job $JOB_ID running because --keep-job was set"
  fi

  exit "$status"
}

trap cleanup EXIT INT TERM

submit_job() {
  local sbatch_words remote_script_file rc
  local q_remote_repo_dir q_remote_repo_dir_explicit q_remote_state_root
  local q_remote_git_ref q_server_host q_server_port q_allow_cors_origins
  local q_automation_cors_origins q_session_key q_secret_key q_job_name
  local q_setup_cmd q_start_cmd q_node_bin
  if ((${#SBATCH_ARGS[@]})); then
    sbatch_words=$(quote_words "${SBATCH_ARGS[@]}")
  else
    sbatch_words=""
  fi

  q_remote_repo_dir=$(quote "$REMOTE_REPO_DIR")
  q_remote_repo_dir_explicit=$(quote "$REMOTE_REPO_DIR_EXPLICIT")
  q_remote_state_root=$(quote "$REMOTE_STATE_ROOT")
  q_remote_git_ref=$(quote "$REMOTE_GIT_REF")
  q_server_host=$(quote "$SERVER_HOST")
  q_server_port=$(quote "$SERVER_PORT")
  q_allow_cors_origins=$(quote "$ALLOW_CORS_ORIGINS")
  q_automation_cors_origins=$(quote "$AUTOMATION_CORS_ORIGINS")
  q_session_key=$(quote "$SESSION_KEY")
  q_secret_key=$(quote "$SECRET_KEY")
  q_job_name=$(quote "$JOB_NAME")
  q_setup_cmd=$(quote "$SETUP_CMD")
  q_start_cmd=$(quote "$START_CMD")
  q_node_bin=$(quote "$NODE_BIN")

  remote_script_file=$(mktemp)
  cat >"$remote_script_file" <<REMOTE
set -Eeuo pipefail
umask 077

REMOTE_REPO_DIR=$q_remote_repo_dir
REMOTE_REPO_DIR_EXPLICIT=$q_remote_repo_dir_explicit
REMOTE_STATE_ROOT=$q_remote_state_root
REMOTE_GIT_REF=$q_remote_git_ref
SERVER_HOST=$q_server_host
SERVER_PORT=$q_server_port
ALLOW_CORS_ORIGINS=$q_allow_cors_origins
AUTOMATION_CORS_ORIGINS=$q_automation_cors_origins
SESSION_KEY=$q_session_key
SECRET_KEY=$q_secret_key
JOB_NAME=$q_job_name
SETUP_CMD=$q_setup_cmd
START_CMD=$q_start_cmd
NODE_BIN=$q_node_bin
SBATCH_ARGS=($sbatch_words)

expand_path() {
  local path=\$1
  if [[ "\$path" == "~" ]]; then
    printf '%s\n' "\$HOME"
  elif [[ "\$path" == "~/"* ]]; then
    printf '%s/%s\n' "\$HOME" "\${path#\~/}"
  else
    printf '%s\n' "\$path"
  fi
}

REMOTE_REPO_DIR=\$(expand_path "\$REMOTE_REPO_DIR")
REMOTE_STATE_ROOT=\$(expand_path "\$REMOTE_STATE_ROOT")

if [[ "\$REMOTE_REPO_DIR_EXPLICIT" -eq 0 ]]; then
  repo_candidates=("\$REMOTE_REPO_DIR" "\$HOME/homework" "\$HOME/homework/agent-canvas")
  for candidate in "\${repo_candidates[@]}"; do
    if [[ -f "\$candidate/package.json" && -f "\$candidate/bin/agent-canvas.mjs" ]]; then
      REMOTE_REPO_DIR="\$candidate"
      break
    fi
    if [[ -f "\$candidate/agent-canvas/package.json" && -f "\$candidate/agent-canvas/bin/agent-canvas.mjs" ]]; then
      REMOTE_REPO_DIR="\$candidate/agent-canvas"
      break
    fi
  done
fi

if [[ "\$REMOTE_REPO_DIR_EXPLICIT" -eq 0 && ! -f "\$REMOTE_REPO_DIR/package.json" && -d "\$REMOTE_REPO_DIR/agent-canvas" ]]; then
  REMOTE_REPO_DIR="\$REMOTE_REPO_DIR/agent-canvas"
fi

trimmed_repo_dir="\${REMOTE_REPO_DIR%/}"
if [[ ! -f "\$REMOTE_REPO_DIR/package.json" && "\${trimmed_repo_dir##*/}" == "software-agent-sdk" && -d "\${trimmed_repo_dir%/*}/agent-canvas" ]]; then
  REMOTE_REPO_DIR="\${trimmed_repo_dir%/*}/agent-canvas"
  printf 'remote repo pointed at software-agent-sdk; using sibling agent-canvas checkout: %s\n' "\$REMOTE_REPO_DIR" >&2
fi

if [[ ! -d "\$REMOTE_REPO_DIR" ]]; then
  printf 'remote agent-canvas checkout not found: %s\n' "\$REMOTE_REPO_DIR" >&2
  exit 2
fi

if [[ ! -f "\$REMOTE_REPO_DIR/package.json" || ! -f "\$REMOTE_REPO_DIR/bin/agent-canvas.mjs" ]]; then
  printf 'remote directory does not look like an agent-canvas checkout: %s\n' "\$REMOTE_REPO_DIR" >&2
  printf 'pass --remote-repo with the OpenHands agent-canvas checkout path if needed\n' >&2
  exit 2
fi

mkdir -p "\$REMOTE_STATE_ROOT"
chmod 700 "\$REMOTE_STATE_ROOT"

timestamp=\$(date +%Y%m%d-%H%M%S)
state_dir="\$REMOTE_STATE_ROOT/\$JOB_NAME-\$timestamp-\$$"
mkdir -p "\$state_dir"
chmod 700 "\$state_dir"

if [[ -n "\$REMOTE_GIT_REF" ]]; then
  if ! git -C "\$REMOTE_REPO_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf 'remote agent-canvas directory is not a git checkout: %s\n' "\$REMOTE_REPO_DIR" >&2
    exit 2
  fi

  git -C "\$REMOTE_REPO_DIR" fetch --quiet origin "\$REMOTE_GIT_REF" >&2
  resolved_ref=\$(git -C "\$REMOTE_REPO_DIR" rev-parse --verify FETCH_HEAD)
  worktree_dir="\$state_dir/agent-canvas"
  git -C "\$REMOTE_REPO_DIR" worktree add --quiet --detach "\$worktree_dir" "\$resolved_ref" >&2
  REMOTE_REPO_DIR="\$worktree_dir"
fi

bin_dir="\$state_dir/bin"
mkdir -p "\$bin_dir"
agent_canvas_bin="\$bin_dir/agent-canvas"
{
  printf '#!/usr/bin/env bash\n'
  printf 'set -Eeuo pipefail\n'
  printf 'node_bin=\${OH_NODE_BIN:-}\n'
  printf 'if [[ -z "\$node_bin" ]]; then\n'
  printf '  if command -v node >/dev/null 2>&1; then\n'
  printf '    node_bin=\$(command -v node)\n'
  printf '  else\n'
  printf '    shopt -s nullglob\n'
  printf '    node_candidates=(/usr/bin/node /usr/local/bin/node "\$HOME"/.local/bin/node "\$HOME"/.nvm/versions/node/*/bin/node)\n'
  printf '    for candidate in "\${node_candidates[@]}"; do\n'
  printf '      if [[ -x "\$candidate" ]]; then\n'
  printf '        node_bin=\$candidate\n'
  printf '      fi\n'
  printf '    done\n'
  printf '    shopt -u nullglob\n'
  printf '  fi\n'
  printf 'fi\n'
  printf 'if [[ -z "\$node_bin" || ! -x "\$node_bin" ]]; then\n'
  printf '  echo "node not found; set OH_NODE_BIN to the remote node executable path" >&2\n'
  printf '  exit 127\n'
  printf 'fi\n'
  printf 'export PATH="\${node_bin%%/*}:\$PATH"\n'
  printf 'exec "\$node_bin" %q "\$@"\n' "\$REMOTE_REPO_DIR/bin/agent-canvas.mjs"
} > "\$agent_canvas_bin"
chmod 700 "\$agent_canvas_bin"

job_script="\$state_dir/job.sbatch"
{
  printf '#!/usr/bin/env bash\n'
  printf '#SBATCH --job-name=%s\n' "\$JOB_NAME"
  printf '#SBATCH --output=%s/slurm-%%j.out\n' "\$state_dir"
  printf '#SBATCH --error=%s/slurm-%%j.err\n' "\$state_dir"
  printf '\n'
  printf 'set -Eeuo pipefail\n'
  printf 'umask 077\n'
  printf 'export PATH=%q:"\$HOME/.local/bin:\$PATH"\n' "\$bin_dir"
  if [[ -n "\$NODE_BIN" ]]; then
    printf 'export OH_NODE_BIN=%q\n' "\$NODE_BIN"
  fi
  printf 'export PYTHONUNBUFFERED=1\n'
  printf 'export OPENHANDS_SUPPRESS_BANNER=1\n'
  printf 'export OH_AGENT_SERVER_HOST=%q\n' "\$SERVER_HOST"
  printf 'export OH_AGENT_SERVER_PORT=%q\n' "\$SERVER_PORT"
  printf 'export PORT=%q\n' "\$SERVER_PORT"
  printf 'export LOCAL_BACKEND_API_KEY=%q\n' "\$SESSION_KEY"
  printf 'export OH_SESSION_API_KEYS_0=%q\n' "\$SESSION_KEY"
  printf 'export OH_SECRET_KEY=%q\n' "\$SECRET_KEY"
  printf 'export OH_ALLOW_CORS_ORIGINS=%q\n' "\$ALLOW_CORS_ORIGINS"
  printf 'export AUTOMATION_CORS_ORIGINS=%q\n' "\$AUTOMATION_CORS_ORIGINS"
  printf 'REMOTE_REPO_DIR=%q\n' "\$REMOTE_REPO_DIR"
  printf 'SETUP_CMD=%q\n' "\$SETUP_CMD"
  printf 'START_CMD=%q\n' "\$START_CMD"
  cat <<'JOB_BODY'

cd "\$REMOTE_REPO_DIR"

echo "[\$(date -Is)] running on \$(hostname)"
echo "[\$(date -Is)] repo: \$REMOTE_REPO_DIR"
if git -C "\$REMOTE_REPO_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "[\$(date -Is)] ref: \$(git -C "\$REMOTE_REPO_DIR" rev-parse --abbrev-ref HEAD) @ \$(git -C "\$REMOTE_REPO_DIR" rev-parse --short HEAD)"
fi

if [[ -n "\$SETUP_CMD" ]]; then
  echo "[\$(date -Is)] setup: \$SETUP_CMD"
  bash -lc "\$SETUP_CMD"
fi

echo "[\$(date -Is)] starting Agent Canvas backend ingress on \${OH_AGENT_SERVER_HOST}:\${OH_AGENT_SERVER_PORT}"
exec bash -lc "\$START_CMD"
JOB_BODY
} > "\$job_script"
chmod 700 "\$job_script"

job_id=\$(sbatch --parsable "\${SBATCH_ARGS[@]}" "\$job_script")
job_id="\${job_id%%;*}"

printf 'JOB_ID=%s\n' "\$job_id"
printf 'STATE_DIR=%s\n' "\$state_dir"
printf 'JOB_SCRIPT=%s\n' "\$job_script"
REMOTE

  ssh "${SSH_OPTS[@]}" "$LOGIN" 'bash -s' <"$remote_script_file"
  rc=$?
  rm -f "$remote_script_file"
  return "$rc"
}

job_snapshot() {
  local remote_script_file q_job_id rc
  q_job_id=$(quote "$JOB_ID")
  remote_script_file=$(mktemp)
  cat >"$remote_script_file" <<REMOTE
set -Eeuo pipefail
job_id=$q_job_id

line=\$(squeue -h -j "\$job_id" -o '%T|%N|%R' | head -n 1 || true)
if [[ -n "\$line" ]]; then
  IFS='|' read -r state nodes reason <<<"\$line"
  node=
  if [[ "\$state" == "RUNNING" && -n "\$nodes" && "\$nodes" != "N/A" && "\$nodes" != "(None)" ]]; then
    node=\$(scontrol show hostnames "\$nodes" 2>/dev/null | head -n 1 || true)
  fi
  printf 'SOURCE=squeue\n'
  printf 'STATE=%s\n' "\$state"
  printf 'NODES=%s\n' "\$nodes"
  printf 'REASON=%s\n' "\$reason"
  printf 'NODE=%s\n' "\$node"
  exit 0
fi

if command -v sacct >/dev/null 2>&1; then
  sacct_line=\$(sacct -n -P -j "\$job_id" --format=State,NodeList,ExitCode 2>/dev/null | head -n 1 || true)
  if [[ -n "\$sacct_line" ]]; then
    IFS='|' read -r state nodes exit_code <<<"\$sacct_line"
    printf 'SOURCE=sacct\n'
    printf 'STATE=%s\n' "\$state"
    printf 'NODES=%s\n' "\$nodes"
    printf 'REASON=%s\n' "\$exit_code"
    printf 'NODE=\n'
    exit 0
  fi
fi

printf 'SOURCE=missing\n'
printf 'STATE=UNKNOWN\n'
printf 'NODES=\n'
printf 'REASON=job not found in squeue or sacct\n'
printf 'NODE=\n'
REMOTE

  ssh "${SSH_OPTS[@]}" "$LOGIN" 'bash -s' <"$remote_script_file"
  rc=$?
  rm -f "$remote_script_file"
  return "$rc"
}

tail_remote_logs_hint() {
  [[ -n ${REMOTE_STATE_DIR:-} ]] || return 0
  printf 'Remote logs:\n' >&2
  printf '  ssh %s %q\n' "$LOGIN" "tail -n 80 $REMOTE_STATE_DIR/slurm-$JOB_ID.out $REMOTE_STATE_DIR/slurm-$JOB_ID.err" >&2
}

log "submitting Slurm job from $LOGIN"
submit_output=$(submit_job)
parse_kv "$submit_output"
[[ -n $JOB_ID ]] || die "could not parse Slurm job id from submission output: $submit_output"

log "submitted Slurm job $JOB_ID"
log "remote state directory: $REMOTE_STATE_DIR"

deadline=$((SECONDS + QUEUE_TIMEOUT))
last_status=
while :; do
  SNAPSHOT_SOURCE=
  SNAPSHOT_STATE=
  SNAPSHOT_NODES=
  SNAPSHOT_REASON=
  SNAPSHOT_NODE=

  snapshot_output=$(job_snapshot || true)
  parse_kv "$snapshot_output"

  if [[ -n $SNAPSHOT_NODE ]]; then
    COMPUTE_NODE=$SNAPSHOT_NODE
    break
  fi

  status="${SNAPSHOT_STATE:-UNKNOWN}"
  if [[ -n ${SNAPSHOT_REASON:-} ]]; then
    status+=" (${SNAPSHOT_REASON})"
  fi
  if [[ $status != "$last_status" ]]; then
    log "waiting for Slurm allocation: $status"
    last_status=$status
  fi

  case "${SNAPSHOT_STATE:-}" in
    CANCELLED*|COMPLETED*|DEADLINE*|FAILED*|NODE_FAIL*|OUT_OF_MEMORY*|PREEMPTED*|TIMEOUT*)
      tail_remote_logs_hint
      die "Slurm job $JOB_ID ended before a node was allocated: ${SNAPSHOT_STATE:-UNKNOWN} ${SNAPSHOT_REASON:-}"
      ;;
  esac

  if ((SECONDS >= deadline)); then
    tail_remote_logs_hint
    die "timed out waiting for Slurm job $JOB_ID to start"
  fi

  sleep "$POLL_INTERVAL"
done

log "Slurm job $JOB_ID is running on $COMPUTE_NODE"

if [[ -n $COMPUTE_USER ]]; then
  COMPUTE_TARGET="$COMPUTE_USER@$COMPUTE_NODE"
elif [[ $LOGIN == *@* ]]; then
  COMPUTE_TARGET="${LOGIN%@*}@$COMPUTE_NODE"
else
  COMPUTE_TARGET="$COMPUTE_NODE"
fi

log "opening tunnel: ${LOCAL_BIND}:${LOCAL_PORT} -> ${COMPUTE_TARGET}:127.0.0.1:${SERVER_PORT} via $LOGIN"
ssh "${SSH_OPTS[@]}" \
  -J "$LOGIN" \
  -L "${LOCAL_BIND}:${LOCAL_PORT}:127.0.0.1:${SERVER_PORT}" \
  -N "$COMPUTE_TARGET" &
TUNNEL_PID=$!

sleep 1
if ! kill -0 "$TUNNEL_PID" >/dev/null 2>&1; then
  wait "$TUNNEL_PID" || true
  die "SSH tunnel failed to start"
fi

curl_host=$LOCAL_BIND
case "$curl_host" in
  0.0.0.0|::) curl_host=127.0.0.1 ;;
esac
LOCAL_URL="http://${curl_host}:${LOCAL_PORT}"

log "waiting for Agent Canvas backend health at ${LOCAL_URL}/health"
deadline=$((SECONDS + SERVER_TIMEOUT))
until curl -fsS --max-time 2 "${LOCAL_URL}/health" >/dev/null 2>&1; do
  if ! kill -0 "$TUNNEL_PID" >/dev/null 2>&1; then
    wait "$TUNNEL_PID" || true
    tail_remote_logs_hint
    die "SSH tunnel exited before the Agent Canvas backend became healthy"
  fi
  if ((SECONDS >= deadline)); then
    tail_remote_logs_hint
    die "timed out waiting for the Agent Canvas backend to become healthy"
  fi
  sleep 2
done

local_state_root=${XDG_RUNTIME_DIR:-$HOME/.cache}/openhands-slurm-tunnel
mkdir -p "$local_state_root"
chmod 700 "$local_state_root"
LOCAL_ENV_FILE="$local_state_root/${JOB_NAME}-${JOB_ID}.env"
{
  printf 'OPENHANDS_AGENT_SERVER_URL=%q\n' "$LOCAL_URL"
  printf 'AGENT_CANVAS_INGRESS_URL=%q\n' "$LOCAL_URL"
  printf 'OPENHANDS_AUTOMATION_API_URL=%q\n' "${LOCAL_URL}/api/automation"
  printf 'OPENHANDS_AUTOMATION_API_KEY=%q\n' "$SESSION_KEY"
  printf 'OH_SESSION_API_KEYS_0=%q\n' "$SESSION_KEY"
  printf 'SLURM_JOB_ID=%q\n' "$JOB_ID"
  printf 'SLURM_NODE=%q\n' "$COMPUTE_NODE"
  printf 'REMOTE_STATE_DIR=%q\n' "$REMOTE_STATE_DIR"
} >"$LOCAL_ENV_FILE"
chmod 600 "$LOCAL_ENV_FILE"

printf '\n'
printf 'Agent Canvas backend stack is reachable through the tunnel.\n'
printf '  Ingress URL: %s\n' "$LOCAL_URL"
printf '  Automation API: %s/api/automation\n' "$LOCAL_URL"
printf '  Automation docs: %s/api/automation/docs\n' "$LOCAL_URL"
printf '  Env file: %s\n' "$LOCAL_ENV_FILE"
printf '  Slurm job: %s on %s\n' "$JOB_ID" "$COMPUTE_NODE"
printf '\n'
printf 'Press Ctrl-C to close the tunnel and cancel the Slurm job.\n'
if [[ $KEEP_JOB -eq 1 ]]; then
  printf 'Because --keep-job is set, Ctrl-C will close the tunnel but leave the Slurm job running.\n'
fi

while kill -0 "$TUNNEL_PID" >/dev/null 2>&1; do
  sleep 15

  SNAPSHOT_SOURCE=
  SNAPSHOT_STATE=
  SNAPSHOT_NODES=
  SNAPSHOT_REASON=
  SNAPSHOT_NODE=
  snapshot_output=$(job_snapshot || true)
  parse_kv "$snapshot_output"
  case "${SNAPSHOT_STATE:-UNKNOWN}" in
    RUNNING|PENDING|CONFIGURING|COMPLETING)
      ;;
    UNKNOWN|"")
      log "Slurm job status unavailable; keeping tunnel open"
      ;;
    *)
      log "Slurm job $JOB_ID is no longer active: ${SNAPSHOT_STATE:-UNKNOWN} ${SNAPSHOT_REASON:-}"
      break
      ;;
  esac
done
