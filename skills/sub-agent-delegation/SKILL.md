---
name: sub-agent-delegation
description: Delegate substantial, self-contained tasks to sub-agents for parallel execution. Supports OpenHands Cloud API and the built-in DelegateTool.
triggers:
- delegate task
- sub-agent
- spawn agent
- parallel task
- delegate to agent
---

# Sub-Agent Delegation

Delegate work that is substantial (several minutes+), self-contained, and parallelizable. Good: cross-repo research, isolated refactors, eval/test runs, separate documentation, multiple issue investigations. Bad: quick lookups, tightly coordinated edits, tasks needing live user interaction.

## Methods

| Factor | DelegateTool | Cloud API |
|--------|--------------|-----------|
| Need | Tool available in current session | `OPENHANDS_CLOUD_API_KEY` |
| Execution | In-process parallel sub-agents | Separate cloud sandboxes |
| Workspace | Shared | Fresh repo clone |
| Results | Consolidated automatically | Poll manually |
| Best for | Related subtasks | Independent background jobs |

If neither is available, do tasks sequentially.

## DelegateTool

Spawn named agents, then delegate tasks; the call blocks until all complete and returns consolidated per-agent results/errors. Agents share LLM config/workspace but have separate context.

```json
{"command": "spawn", "ids": ["research", "implementation", "testing"]}
```

```json
{
  "command": "delegate",
  "tasks": {
    "research": "Find best practices for async error handling in Python",
    "implementation": "Refactor the database module to use connection pooling",
    "testing": "Write integration tests for the new API endpoints"
  }
}
```

## OpenHands Cloud API

Creates independent conversations. Docs: [Cloud API](https://docs.openhands.dev/openhands/usage/cloud/cloud-api).

Start a conversation (V1 returns a start task):

```bash
curl -X POST "https://app.all-hands.dev/api/v1/app-conversations" \
  -H "Authorization: Bearer $OPENHANDS_CLOUD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"initial_message":{"content":[{"type":"text","text":"Your task description here"}]},"selected_repository":"owner/repo"}'
```

Response shape is `{ "id": "START_TASK_ID", "status": "WORKING" }`. Start-task statuses: `WORKING`, `WAITING_FOR_SANDBOX`, `PREPARING_REPOSITORY`, `STARTING_CONVERSATION`, `READY` (then read `app_conversation_id`), `ERROR`.

Poll start task:

```bash
curl -s "https://app.all-hands.dev/api/v1/app-conversations/start-tasks?ids=START_TASK_ID" \
  -H "Authorization: Bearer $OPENHANDS_CLOUD_API_KEY"
```

When ready, the start-task response includes `app_conversation_id`; use it to check execution.

Check conversation/list conversations:

```bash
curl -s "https://app.all-hands.dev/api/v1/app-conversations?ids=CONVERSATION_ID" \
  -H "Authorization: Bearer $OPENHANDS_CLOUD_API_KEY"

curl -s "https://app.all-hands.dev/api/v1/app-conversations/search?limit=20" \
  -H "Authorization: Bearer $OPENHANDS_CLOUD_API_KEY"
```

Conversation search returns `items` plus `next_page_id`. Conversation `execution_status`: `idle`, `running`, `paused`, `waiting_for_confirmation`, `error`, `finished`. `sandbox_status`: `STARTING`, `RUNNING`, `PAUSED`, `ERROR`, `MISSING`.

Compact Python helper:

```python
import os, time, requests
BASE_URL = "https://app.all-hands.dev"

def session():
    key = os.environ["OPENHANDS_CLOUD_API_KEY"]
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    return s

def delegate_to_cloud(task: str, repo: str, wait: bool = True) -> dict:
    s = session()
    r = s.post(f"{BASE_URL}/api/v1/app-conversations", json={
        "initial_message": {"content": [{"type": "text", "text": task}]},
        "selected_repository": repo,
    })
    r.raise_for_status()
    start_id = r.json()["id"]
    out = {"start_task_id": start_id, "conversation_id": None}
    if not wait:
        return out
    for _ in range(60):
        t = s.get(f"{BASE_URL}/api/v1/app-conversations/start-tasks", params={"ids": start_id}).json()
        if t and t[0].get("status") == "READY":
            out["conversation_id"] = t[0].get("app_conversation_id")
            print(f"{BASE_URL}/conversations/{out['conversation_id']}")
            return out
        if t and t[0].get("status") == "ERROR":
            raise RuntimeError(t[0])
        time.sleep(5)
    raise TimeoutError("Timed out waiting for conversation")

def get_conversation_status(conversation_id: str) -> dict | None:
    r = session().get(f"{BASE_URL}/api/v1/app-conversations", params={"ids": conversation_id})
    r.raise_for_status()
    data = r.json()
    return data[0] if data else None

def list_conversations(limit: int = 20) -> list:
    r = session().get(f"{BASE_URL}/api/v1/app-conversations/search", params={"limit": limit})
    r.raise_for_status()
    return r.json().get("items", [])

def check_delegated_tasks(conversation_ids: list[str] | None = None) -> dict:
    if conversation_ids:
        r = session().get(f"{BASE_URL}/api/v1/app-conversations", params={"ids": ",".join(conversation_ids)})
        conversations = r.json()
    else:
        conversations = list_conversations(50)
    buckets = {"running": [], "finished": [], "other": []}
    for c in filter(None, conversations):
        item = {"conversation_id": c.get("id"), "repository": c.get("selected_repository", ""), "sandbox_status": c.get("sandbox_status"), "execution_status": c.get("execution_status"), "url": f"{BASE_URL}/conversations/{c.get('id')}"}
        buckets["running" if item["execution_status"] == "running" else "finished" if item["execution_status"] == "finished" else "other"].append(item)
    return buckets
```

## Cloud Rate Limit

Do not run more than 5 cloud delegations at once. Before starting more, count running conversations and use only available slots:

```python
running = [c for c in list_conversations(50) if c.get("execution_status") == "running"]
if len(running) >= 5:
    print(f"Wait: {len(running)} tasks already running")
else:
    print(f"Can delegate {5 - len(running)} more tasks")
```

## Delegation Prompts

Sub-agents lack your conversation context. Include repo, branch/PR, paths, requirements, expected output, and fallback/error handling. For PR work, tell them to follow the [iterate skill](https://github.com/OpenHands/extensions/tree/main/skills/iterate) rather than pasting PR instructions.

```text
Fix unresolved review comments in PR #123.
Follow the OpenHands/extensions iterate skill to drive the PR through CI, review, and QA until merge-ready or genuinely blocked.
Return: changes made, verification results, unresolved blockers.
```

## Availability Check

```python
delegate_available = "DelegateTool" in [t.name for t in available_tools]
cloud_available = os.environ.get("OPENHANDS_CLOUD_API_KEY") is not None
```

References: [SDK delegation guide](https://docs.openhands.dev/sdk/guides/agent-delegation), [Cloud API](https://docs.openhands.dev/openhands/usage/cloud/cloud-api), [API reference](https://docs.openhands.dev/api-reference).
