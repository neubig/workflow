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

This skill explains how to delegate substantial, self-contained tasks to sub-agents for parallel or background execution.

## When to Delegate

Delegate tasks when they are:
- **Substantial**: Would take several minutes or more to complete
- **Self-contained**: Have clear inputs and outputs, minimal dependencies on current context
- **Parallelizable**: Can run independently without blocking your main workflow

Good candidates:
- Research tasks across multiple repositories
- Code refactoring in isolated modules
- Running evaluations or test suites
- Generating documentation for separate components
- Investigating multiple issues simultaneously

Poor candidates:
- Quick lookups or simple commands
- Tasks requiring tight coordination with current work
- Tasks needing real-time interaction with the user

## Delegation Methods

There are two ways to delegate tasks, depending on available tools:

### Method 1: DelegateTool (In-Process)

Use when `DelegateTool` is available in your tool set. Sub-agents run in parallel within the same session.

#### Step 1: Spawn Sub-Agents

```json
{
    "command": "spawn",
    "ids": ["research", "implementation", "testing"]
}
```

Each sub-agent:
- Gets a unique identifier you specify
- Inherits the same LLM configuration
- Operates in the same workspace
- Maintains its own conversation context

#### Step 2: Delegate Tasks

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

The delegate operation:
- Runs all tasks in parallel
- Blocks until all sub-agents complete
- Returns consolidated results from all sub-agents
- Handles errors gracefully per sub-agent

#### Complete Example

```python
# 1. Spawn sub-agents for parallel work
{
    "command": "spawn",
    "ids": ["frontend", "backend"]
}

# 2. Delegate tasks
{
    "command": "delegate",
    "tasks": {
        "frontend": "Update all React components to use the new design system",
        "backend": "Migrate the API endpoints to use async handlers"
    }
}

# 3. Results are automatically consolidated
# Continue with merged results from both sub-agents
```

### Method 2: OpenHands Cloud API (Remote)

Use when `OPENHANDS_CLOUD_API_KEY` is available. Creates separate cloud conversations that run independently.

**Documentation**: See [OpenHands Cloud API docs](https://docs.openhands.dev/openhands/usage/cloud/cloud-api) for the full API reference.

#### Step 1: Start a Delegated Conversation (V1 API)

```bash
curl -X POST "https://app.all-hands.dev/api/v1/app-conversations" \
  -H "Authorization: Bearer $OPENHANDS_CLOUD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "initial_message": {
      "content": [{"type": "text", "text": "Your task description here"}]
    },
    "selected_repository": "owner/repo"
  }'
```

**Response** (returns a start task, not the conversation directly):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "WORKING"
}
```

Start task status values:
- `WORKING` - Initial processing
- `WAITING_FOR_SANDBOX` - Waiting for sandbox allocation
- `PREPARING_REPOSITORY` - Cloning repository  
- `STARTING_CONVERSATION` - Starting the agent
- `READY` - Conversation is active (check `app_conversation_id`)
- `ERROR` - An error occurred

#### Step 2: Poll Start Task Until Ready

```bash
curl -s "https://app.all-hands.dev/api/v1/app-conversations/start-tasks?ids=START_TASK_ID" \
  -H "Authorization: Bearer $OPENHANDS_CLOUD_API_KEY"
```

**Response when ready:**
```json
[{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "READY",
  "app_conversation_id": "660e8400-e29b-41d4-a716-446655440001"
}]
```

#### Step 3: Check Conversation Execution Status

Once you have the `app_conversation_id`, check if the agent has completed:

```bash
curl -s "https://app.all-hands.dev/api/v1/app-conversations?ids=CONVERSATION_ID" \
  -H "Authorization: Bearer $OPENHANDS_CLOUD_API_KEY"
```

**Response:**
```json
[{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "sandbox_status": "RUNNING",
  "execution_status": "running",
  "selected_repository": "owner/repo"
}]
```

**`execution_status` values:**
- `idle` - Waiting for user input
- `running` - Agent is actively working
- `paused` - Conversation is paused
- `waiting_for_confirmation` - Agent needs user confirmation
- `error` - An error occurred
- `finished` - Agent completed successfully

**`sandbox_status` values:**
- `STARTING` - Sandbox is starting up
- `RUNNING` - Sandbox is active
- `PAUSED` - Sandbox is paused (idle timeout)
- `ERROR` - Sandbox error
- `MISSING` - Sandbox no longer exists

#### List All Conversations

```bash
curl -s "https://app.all-hands.dev/api/v1/app-conversations/search?limit=20" \
  -H "Authorization: Bearer $OPENHANDS_CLOUD_API_KEY"
```

**Response:**
```json
{
  "items": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "sandbox_status": "RUNNING",
      "execution_status": "finished",
      "selected_repository": "owner/repo"
    }
  ],
  "next_page_id": null
}
```

#### Python Helper

```python
import os
import time
import requests

BASE_URL = "https://app.all-hands.dev"

def get_session():
    """Create authenticated session."""
    api_key = os.environ.get("OPENHANDS_CLOUD_API_KEY")
    if not api_key:
        raise ValueError("OPENHANDS_CLOUD_API_KEY not set")
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    })
    return session

def delegate_to_cloud(task: str, repo: str, wait_for_ready: bool = True) -> dict:
    """Delegate a task to a new OpenHands Cloud conversation (V1 API).
    
    Args:
        task: Task description for the agent
        repo: Repository in 'owner/repo' format
        wait_for_ready: If True, poll until conversation is ready
        
    Returns:
        Dict with 'start_task_id' and 'conversation_id' (if ready)
    """
    session = get_session()
    
    # Step 1: Start the conversation
    response = session.post(
        f"{BASE_URL}/api/v1/app-conversations",
        json={
            "initial_message": {
                "content": [{"type": "text", "text": task}]
            },
            "selected_repository": repo
        }
    )
    response.raise_for_status()
    start_task = response.json()
    start_task_id = start_task["id"]
    
    result = {"start_task_id": start_task_id, "conversation_id": None}
    
    if not wait_for_ready:
        return result
    
    # Step 2: Poll until ready
    for _ in range(60):  # Max 5 minutes
        response = session.get(
            f"{BASE_URL}/api/v1/app-conversations/start-tasks",
            params={"ids": start_task_id}
        )
        tasks = response.json()
        if tasks and tasks[0].get("status") == "READY":
            result["conversation_id"] = tasks[0].get("app_conversation_id")
            print(f"Delegated task to: {BASE_URL}/conversations/{result['conversation_id']}")
            return result
        elif tasks and tasks[0].get("status") == "ERROR":
            raise RuntimeError(f"Start task failed: {tasks[0]}")
        time.sleep(5)
    
    raise TimeoutError("Timed out waiting for conversation to start")


def get_conversation_status(conversation_id: str) -> dict:
    """Get the current status of a conversation."""
    session = get_session()
    response = session.get(
        f"{BASE_URL}/api/v1/app-conversations",
        params={"ids": conversation_id}
    )
    response.raise_for_status()
    conversations = response.json()
    return conversations[0] if conversations else None


def list_conversations(limit: int = 20) -> list:
    """List recent conversations."""
    session = get_session()
    response = session.get(
        f"{BASE_URL}/api/v1/app-conversations/search",
        params={"limit": limit}
    )
    response.raise_for_status()
    return response.json().get("items", [])


def check_delegated_tasks(conversation_ids: list[str] = None) -> dict:
    """Check status of delegated tasks.
    
    Args:
        conversation_ids: List of conversation IDs to check.
                         If None, lists recent conversations.
    
    Returns:
        Dict with 'running', 'finished', and 'other' lists.
    """
    if conversation_ids:
        # Batch get specific conversations
        session = get_session()
        response = session.get(
            f"{BASE_URL}/api/v1/app-conversations",
            params={"ids": ",".join(conversation_ids)}
        )
        conversations = response.json()
    else:
        conversations = list_conversations(limit=50)
    
    running = []
    finished = []
    other = []
    
    for conv in conversations:
        if conv is None:
            continue
        info = {
            "conversation_id": conv.get("id"),
            "repository": conv.get("selected_repository", ""),
            "sandbox_status": conv.get("sandbox_status"),
            "execution_status": conv.get("execution_status"),
            "url": f"{BASE_URL}/conversations/{conv.get('id')}"
        }
        
        exec_status = conv.get("execution_status", "")
        if exec_status == "running":
            running.append(info)
        elif exec_status == "finished":
            finished.append(info)
        else:
            other.append(info)
    
    return {"running": running, "finished": finished, "other": other}
```

## Choosing a Method

| Factor | DelegateTool | Cloud API |
|--------|--------------|-----------|
| Availability | Tool must be in tool set | Requires `OPENHANDS_CLOUD_API_KEY` |
| Execution | In-process, parallel | Separate cloud sandboxes |
| Workspace | Shared with parent | Fresh clone of repository |
| Results | Automatic consolidation | Manual status polling |
| Best for | Tightly related subtasks | Independent background jobs |

## Best Practices

1. **Write clear task descriptions**: Sub-agents have no context from your conversation
2. **Include all necessary information**: Repository names, file paths, specific requirements
3. **Set appropriate expectations**: Describe the expected output format
4. **Check for availability**: Verify `DelegateTool` is in tools or `OPENHANDS_CLOUD_API_KEY` is set before attempting delegation
5. **Handle failures gracefully**: Sub-agents may fail; have a fallback plan

## Rate Limits for OpenHands Cloud API

<IMPORTANT>
**Do not delegate more than 5 tasks at a time** via the OpenHands Cloud API to avoid hitting rate limits.

Before delegating new tasks:
1. Check how many conversations are currently running
2. Wait for some to complete if there are already 5+ running
3. Then delegate new tasks in batches of 5 or fewer

**Check running conversations before delegating:**
```python
def count_running_conversations() -> int:
    """Count currently running conversations."""
    session = get_session()
    response = session.get(
        f"{BASE_URL}/api/v1/app-conversations/search",
        params={"limit": 50}
    )
    conversations = response.json().get("items", [])
    running = [c for c in conversations if c.get("execution_status") == "running"]
    return len(running)

# Before delegating
running_count = count_running_conversations()
if running_count >= 5:
    print(f"Warning: {running_count} tasks already running. Wait for some to complete.")
else:
    available_slots = 5 - running_count
    print(f"Can delegate up to {available_slots} new tasks")
```
</IMPORTANT>

## Delegating PR Fix Tasks

When delegating PR tasks, instruct sub-agents to follow the [github-pr-workflow](../github-pr-workflow/SKILL.md) skill and its PR Readiness Checklist.

**Example task description:**
```
Fix unresolved review comments in PR #123.

Follow the github-pr-workflow skill PR Readiness Checklist:
- Gather END-TO-END evidence (not unit tests)
- Resolve all review threads
- Wait for CI to pass
- Check for no extra unnecessary code
- Only mark ready when ALL conditions pass
```

## Checking Delegation Availability

```python
# Check for DelegateTool
delegate_available = "DelegateTool" in [t.name for t in available_tools]

# Check for Cloud API
cloud_available = os.environ.get("OPENHANDS_CLOUD_API_KEY") is not None

if delegate_available:
    # Use DelegateTool for in-process delegation
    pass
elif cloud_available:
    # Use Cloud API for remote delegation
    pass
else:
    # No delegation available - do tasks sequentially
    pass
```

## References

- [OpenHands SDK Sub-Agent Delegation Guide](https://docs.openhands.dev/sdk/guides/agent-delegation)
- [OpenHands Cloud API Documentation](https://docs.openhands.dev/openhands/usage/cloud/cloud-api)
- [API Reference](https://docs.openhands.dev/api-reference)
