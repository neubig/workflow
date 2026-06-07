---
name: tunnel-to-babel
description: Create Agent Canvas backend tunnels on Babel Slurm using openhands-slurm-tunnel.sh, including debug CPU jobs and general-partition GPU jobs that favor L40S. Use when asked to create, start, or document OpenHands/Agent Canvas tunnels to Babel.
triggers:
- tunnel to babel
- babel tunnel
- slurm tunnel
- openhands slurm tunnel
- agent canvas tunnel
---

# Tunnel to Babel

Use this skill to start an authenticated Agent Canvas backend stack in a Babel Slurm job and tunnel it to the local machine.

The source-of-truth script is bundled at:

```bash
skills/tunnel-to-babel/scripts/openhands-slurm-tunnel.sh
```

Use local port `8002` by default. The script reuses `OH_SESSION_API_KEYS_0` when it is already set, falling back to the saved Agent Canvas API key file if needed.

Success means both of these work:

1. Local tunnel health at `http://127.0.0.1:8002/health`.
2. Authenticated public API access through `https://statusquo-amd-ohbabel.ngrok-free.app/api/conversations/search` using `X-Session-API-Key` from `/home/gneubig/.openhands/agent-canvas/api-key.txt`.

The script validates both before printing success. If the public URL fails, fix the local SSH listener or ngrok process instead of treating the tunnel as ready.

## SSH Key Auth

Babel access should use SSH key authentication through the local SSH config alias `babel`, not password auth. The expected local config is:

```sshconfig
Host babel
   HostName login.babel.cs.cmu.edu
   User gneubig
   IdentityFile ~/.ssh/openhands_slurm
   IdentitiesOnly yes
   ServerAliveInterval 60
   ServerAliveCountMax 3
```

The tunnel script defaults to `--login babel` and uses `BatchMode=yes`, so a password prompt means key auth is not set up correctly. Do not wait at the password prompt. Verify key auth with:

```bash
ssh -o BatchMode=yes babel 'hostname'
```

If this fails, fix the local SSH key/config or authorized key on Babel before retrying the tunnel. Override the login only when necessary:

```bash
OH_BABEL_LOGIN=babel skills/tunnel-to-babel/scripts/openhands-slurm-tunnel.sh --help
```

## CPU Tunnel on Debug

Use the debug partition without GPU access:

```bash
OH_SLURM_GRES= skills/tunnel-to-babel/scripts/openhands-slurm-tunnel.sh \
  --partition debug \
  --time 01:00:00 \
  --local-port 8002
```

`OH_SLURM_GRES=` is required because the script otherwise requests `gpu:1` by default.

## GPU Tunnel on General

Favor L40S on the general partition:

```bash
skills/tunnel-to-babel/scripts/openhands-slurm-tunnel.sh \
  --partition general \
  --gres gpu:L40S:1 \
  --time 04:00:00 \
  --local-port 8002 \
  --public-url https://statusquo-amd-ohbabel.ngrok-free.app
```

If Babel exposes L40S through constraints instead of typed GRES, use:

```bash
skills/tunnel-to-babel/scripts/openhands-slurm-tunnel.sh \
  --partition general \
  --gres gpu:1 \
  --constraint L40S \
  --time 04:00:00 \
  --local-port 8002
```

To verify the exact scheduler spelling:

```bash
ssh babel \
  'sinfo -p general -o "%P|%G|%f|%N"'
```

## Useful Options

- `--remote-repo DIR`: Babel-side `agent-canvas` checkout. Default is `~/homework` with `~/homework/agent-canvas` fallback.
- `--remote-ref REF`: fetch and run an isolated detached worktree at the given ref.
- `--keep-job`: close the tunnel without canceling the Slurm job.
- `--public-url URL`: public URL that must route to the local tunnel and pass authenticated API validation. Default is `https://statusquo-amd-ohbabel.ngrok-free.app`.
- `--public-timeout SECONDS`: how long to wait for the public authenticated API check. Default is `120`.
- `--api-check-path PATH`: authenticated API path validated through both local and public URLs. Default is `/api/conversations/search`.
- `--server-port PORT`: backend ingress port on the compute node. Default is `8000`.

The expected API key file is:

```bash
/home/gneubig/.openhands/agent-canvas/api-key.txt
```

Use it like this:

```bash
curl -H "X-Session-API-Key: $(cat /home/gneubig/.openhands/agent-canvas/api-key.txt)" \
  -H "ngrok-skip-browser-warning: 1" \
  https://statusquo-amd-ohbabel.ngrok-free.app/api/conversations/search
```

The ngrok endpoint must be running separately and forwarding to local port `8002`, for example:

```bash
ngrok http 8002 --url statusquo-amd-ohbabel.ngrok-free.app
```

When the tunnel is healthy, the script prints the local ingress URL, public URL, automation API URL, session key file, env file, Slurm job ID, and compute node. Ctrl-C closes the tunnel and cancels the Slurm job unless `--keep-job` was set.
