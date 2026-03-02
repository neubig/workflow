---
name: daily-workflow
description: Graham's daily workflow for managing Linear tickets and GitHub PRs. Prioritizes work by Linear priority, manages PR review cycles, and tracks resources needed for testing.
triggers:
- daily workflow
- my workflow
- graham workflow
---

# Graham's Daily Workflow

This skill implements Graham's specific daily workflow for managing development tasks.

## User Identifiers

- **Linear**: `graham@openhands.dev`
- **GitHub**: `neubig`

## Workflow Overview

The daily workflow consists of four phases executed in order:

```
1. LINEAR TICKETS     →  Work on highest priority first
       ↓
2. READY PRs          →  Check for reviews, ping reviewers if stale
       ↓  
3. DRAFT PRs          →  Address feedback, demonstrate functionality
       ↓
4. ACTION ITEMS       →  Categorized list of items needing user help
```

## Phase 1: Linear Tickets

### Fetch My Assigned Tickets

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "query { viewer { assignedIssues(first: 50, filter: { state: { type: { nin: [\"completed\", \"canceled\"] } } }) { nodes { identifier title priority priorityLabel state { name type } description } } } }"
  }' | jq '.data.viewer.assignedIssues.nodes | sort_by(.priority)'
```

### Priority Order

| Priority | Label | Action |
|----------|-------|--------|
| 1 | Urgent | Work immediately |
| 2 | High | Work first |
| 3 | Medium | After high priority |
| 4 | Low | When time permits |

### Tickets Requiring Manual Action

Some tickets cannot be automated and should be added to a personal action list:
- Tickets with only Slack links
- "Contact X" or "Send email to Y" tasks
- Discussion/meeting requests

## Phase 2: Ready PRs

### Fetch My Ready PRs

```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/search/issues?q=is:pr+is:open+author:neubig+draft:false" \
  | jq '.items[] | {repo: .repository_url | split("/") | .[-1], number: .number, title: .title}'
```

### Check for Unresolved Reviews

For each ready PR, check review status:
```bash
gh api graphql -f query='
{
  repository(owner: "OWNER", name: "REPO") {
    pullRequest(number: PR_NUMBER) {
      reviewThreads(first: 50) {
        nodes { isResolved }
      }
    }
  }
}' | jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length'
```

### Decision Tree

```
Ready PR
├── Has unresolved reviews?
│   └── YES → Move to draft, address feedback
│   └── NO → Ready for 2+ business days?
│       └── YES → Ping reviewer on Slack (manual)
│       └── NO → Wait
```

## Phase 3: Draft PRs

### Fetch My Draft PRs

```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/search/issues?q=is:pr+is:open+author:neubig+draft:true" \
  | jq '.items[] | {repo: .repository_url | split("/") | .[-1], number: .number, title: .title}'
```

### Work on Draft PRs

1. **Address ALL Review Comments** - The agent MUST resolve all unresolved review threads by:
   - Making code changes to fix the issue
   - Replying to the review thread explaining the fix
   - Resolving the thread via the GitHub API
   - Do NOT list reviews as "needing attention" - resolve them yourself

2. **Provide Evidence in PR Description** - REQUIRED for all PRs:
   
   **For Bug Fixes** - Show before/after:
   ```markdown
   ## Evidence
   
   **Before (on main branch):**
   ```
   $ python -c "from openhands.tools import terminal"
   ModuleNotFoundError: No module named 'fcntl'
   ```
   
   **After (this PR):**
   ```
   $ python -c "from openhands.tools import terminal"
   # No error - import succeeds
   ```
   ```
   
   **For Features** - Show it working:
   ```markdown
   ## Evidence
   
   **Feature in action:**
   ```
   $ openhands mcp add figma --transport http https://mcp.figma.com
   ✓ Added Figma MCP server
   
   $ openhands mcp list
   NAME    STATUS    URL
   figma   enabled   https://mcp.figma.com
   ```
   ```

3. **Iterate on Bot Reviews** - Check for new reviews after each fix, repeat until 0 unresolved

<IMPORTANT>
If evidence cannot be gathered due to missing resources (API keys, platforms, etc.),
explain why in the PR description and list what's needed for manual verification.
</IMPORTANT>

## Special Resources Output

When PRs cannot be live tested, always provide a categorized list:

```markdown
## Draft PRs Requiring Special Resources

### 🖥️ Platform/Environment Access
| PR | Description | Resource Needed |
|----|-------------|-----------------|
| repo#123 | Windows fix | **Windows machine** |

### 🔑 API Keys / Credentials
| PR | Description | Resource Needed |
|----|-------------|-----------------|
| repo#456 | New model | **API key** with access |

### 🏗️ CI/CD Infrastructure
| PR | Description | Resource Needed |
|----|-------------|-----------------|
| repo#789 | Jenkins config | **Jenkins server** |

### 📊 External Services
| PR | Description | Resource Needed |
|----|-------------|-----------------|
| repo#101 | Dataset integration | **Dataset access** |
```

After providing the list, ask:
> Would you like me to work on any of these if you can provide the required resources?

## Phase 4: Categorized Action Items

At the end of the workflow, ALWAYS provide a categorized summary of items requiring user help:

```markdown
## 📋 Action Items Requiring Your Help

### 🗣️ Manual Communication (Slack/Email)
| Item | Action Needed |
|------|---------------|
| ALL-1234 | Ping reviewer on Slack (PR stale >2 days) |
| ALL-5678 | Slack link needs manual review |

### 🔑 Credentials / API Keys Needed
| PR | Resource Needed |
|----|-----------------|
| repo#123 | API key for new model testing |

### 🖥️ Platform / Environment Access
| PR | Resource Needed |
|----|-----------------|
| repo#456 | Windows machine for testing |

### 🏗️ CI/CD / Infrastructure
| PR | Resource Needed |
|----|-----------------|
| repo#789 | Jenkins server access |

### ❓ Clarification Needed
| Item | Question |
|------|----------|
| ALL-9999 | Description unclear - what is the expected behavior? |
```

After the list, ask:
> Would you like me to work on any of these if you can provide the required resources or clarification?

## Important Notes

<IMPORTANT>
- ALWAYS end with the categorized action items list above
- Slack pings are manual - include in action items for user
- PRs requiring special resources MUST be categorized
- Iterate on bot reviews until 0 unresolved
- Ask for confirmation before working on unclear tickets
</IMPORTANT>
