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
  --local-port 8002
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
ssh gneubig@login4.babel.cs.cmu.edu \
  'sinfo -p general -o "%P|%G|%f|%N"'
```

## Useful Options

- `--remote-repo DIR`: Babel-side `agent-canvas` checkout. Default is `~/homework` with `~/homework/agent-canvas` fallback.
- `--remote-ref REF`: fetch and run an isolated detached worktree at the given ref.
- `--keep-job`: close the tunnel without canceling the Slurm job.
- `--server-port PORT`: backend ingress port on the compute node. Default is `8000`.

When the tunnel is healthy, the script prints the ingress URL, automation API URL, env file, Slurm job ID, and compute node. Ctrl-C closes the tunnel and cancels the Slurm job unless `--keep-job` was set.
