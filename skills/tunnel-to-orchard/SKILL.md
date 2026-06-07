---
name: tunnel-to-orchard
description: Create login-node tunnels to Orchard through Google Cloud IAP for OpenHands Agent Canvas. Use when asked to connect, tunnel, SSH, SCP, or configure VSCode access for Orchard or orchard-login-001.
triggers:
- tunnel to orchard
- orchard tunnel
- orchard-login-001
- gcloud iap tunnel
- agent canvas orchard
---

# Tunnel to Orchard

Use this skill to connect to Orchard's login node and tunnel a service running on `orchard-login-001` back to the local machine through Google Cloud IAP.

The source-of-truth tunnel script is bundled at:

```bash
skills/tunnel-to-orchard/scripts/openhands-orchard-login-tunnel.sh
```

Defaults:

- GCP project: `cmu-gpu-cloud`
- GCP zone: `us-central1-c`
- Login node: `orchard-login-001`
- Local listener: `127.0.0.1:8003`
- Remote target: `127.0.0.1:8000` on the login node

Success means local tunnel health works at:

```bash
http://127.0.0.1:8003/health
```

If an Agent Canvas session key is already available in `OH_SESSION_API_KEYS_0`, `LOCAL_BACKEND_API_KEY`, or `/home/gneubig/.openhands/agent-canvas/api-key.txt`, the script also validates authenticated API access at `/api/conversations/search`.

## Start the Tunnel

Start or ensure the Agent Canvas backend is already running on the Orchard login node on port `8000`, then run:

```bash
skills/tunnel-to-orchard/scripts/openhands-orchard-login-tunnel.sh
```

Use a different local port if needed:

```bash
skills/tunnel-to-orchard/scripts/openhands-orchard-login-tunnel.sh --local-port 8012
```

Keep a raw IAP tunnel open without checking Agent Canvas health:

```bash
skills/tunnel-to-orchard/scripts/openhands-orchard-login-tunnel.sh --no-health-check
```

## Google Cloud Login

If `gcloud` is not installed, install the Google Cloud CLI using Google's platform-specific instructions.

If `gcloud` is installed but Orchard access fails due to missing credentials, ask the user to run:

```bash
gcloud auth login
gcloud config set compute/zone us-central1-c
gcloud config set project cmu-gpu-cloud
```

Do not attempt to handle browser-based login non-interactively.

## Direct SSH and SCP

Direct SSH through IAP:

```bash
gcloud compute ssh --zone "us-central1-c" "orchard-login-001" --project "cmu-gpu-cloud" --tunnel-through-iap
```

Copy a local file to Orchard:

```bash
gcloud compute scp --zone "us-central1-c" --project "cmu-gpu-cloud" --tunnel-through-iap file.txt orchard-login-001:
```

Copy a file from Orchard:

```bash
gcloud compute scp --zone "us-central1-c" --project "cmu-gpu-cloud" --tunnel-through-iap orchard-login-001:file.txt .
```

## VSCode SSH Config

Use the actual `gcloud` path from `command -v gcloud`:

```sshconfig
Host orchard
  HostName orchard-login-001
  User <your username>
  IdentityFile ~/.ssh/google_compute_engine
  ProxyCommand <path_to_gcloud_bin> compute start-iap-tunnel %h 22 --listen-on-stdin --zone "us-central1-c" --project "cmu-gpu-cloud"
```

If VSCode remote setup fails, check whether the Orchard home directory has enough space for the `.vscode` directory that VSCode uploads.

## SSH Key Repair

If Orchard reports `Permission denied (publickey)` for node-to-node SSH, preserve or repair the key pair in the Orchard home directory. If the original key cannot be restored, generate a new key on Orchard:

```bash
ssh-keygen -t ed25519 -C "[$(whoami)@$(uname -n)-$(date -I)]"
```

Append the generated public key contents to `${HOME}/.ssh/authorized_keys`, then retry SSH.
