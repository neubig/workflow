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

#### Start a Delegated Conversation

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

#### Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "WORKING",
  "app_conversation_id": "660e8400-e29b-41d4-a716-446655440001"
}
```

#### Check Conversation Status

```bash
curl -s -H "Authorization: Bearer $OPENHANDS_CLOUD_API_KEY" \
  "https://app.all-hands.dev/api/v1/app-conversations/$CONVERSATION_ID"
```

Status values:
- `WORKING` - Initial processing
- `WAITING_FOR_SANDBOX` - Waiting for sandbox
- `PREPARING_REPOSITORY` - Cloning repository
- `READY` - Conversation is active
- `ERROR` - An error occurred

#### Python Helper

```python
import os
import requests

def delegate_to_cloud(task: str, repo: str) -> dict:
    """Delegate a task to a new OpenHands Cloud conversation."""
    api_key = os.environ.get("OPENHANDS_CLOUD_API_KEY")
    if not api_key:
        raise ValueError("OPENHANDS_CLOUD_API_KEY not set")
    
    response = requests.post(
        "https://app.all-hands.dev/api/v1/app-conversations",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "initial_message": {
                "content": [{"type": "text", "text": task}]
            },
            "selected_repository": repo
        }
    )
    result = response.json()
    conversation_id = result.get("app_conversation_id") or result.get("id")
    
    print(f"Delegated task to: https://app.all-hands.dev/conversations/{conversation_id}")
    return result
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
