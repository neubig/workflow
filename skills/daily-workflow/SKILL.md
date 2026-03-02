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

> **PR Workflow Details**: See [github-pr-workflow](../github-pr-workflow/SKILL.md) for complete PR handling instructions including live testing, evidence requirements, and review iteration.

## User Identifiers

- **Linear**: `graham@openhands.dev`
- **GitHub**: `neubig`

## Workflow Overview

The daily workflow consists of four phases executed in order:

```
1. LINEAR TICKETS     →  Work on highest priority first
       ↓
2. READY PRs          →  Check for reviews, move to draft if unresolved
       ↓  
3. DRAFT PRs          →  Address feedback per github-pr-workflow skill
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

Add to Phase 4 action items:
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

### Decision Tree

```
Ready PR
├── Has unresolved reviews?
│   └── YES → Move to draft, process in Phase 3
│   └── NO → Ready for 2+ business days?
│       └── YES → Check and report stale PRs (see below)
│       └── NO → No action needed
```

### Check for Stale PRs

The agent checks PR creation dates and reports stale PRs with direct links:

```bash
# Check PR age and report if stale
gh pr list --author neubig --state open --json number,title,createdAt,url \
  | jq -r '.[] | select((now - (.createdAt | fromdateiso8601)) / 86400 > 2) | "\(.url) - \(.title) (created \((now - (.createdAt | fromdateiso8601)) / 86400 | floor) days ago)"'
```

The agent will report:
> **Stale PRs (>2 days without review):**
> - https://github.com/org/repo/pull/123 - Fix bug (created 5 days ago)
> - https://github.com/org/repo/pull/456 - Add feature (created 3 days ago)
>
> Please ping reviewers on Slack for these PRs.

## Phase 3: Draft PRs

### Fetch My Draft PRs

```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/search/issues?q=is:pr+is:open+author:neubig+draft:true" \
  | jq '.items[] | {repo: .repository_url | split("/") | .[-1], number: .number, title: .title}'
```

### Work on Draft PRs

**Follow the [github-pr-workflow](../github-pr-workflow/SKILL.md) skill**, which requires:

1. **Address ALL review comments** - Make fixes, reply, resolve threads via API
2. **Provide evidence** - Before/after for bugs, working demo for features
3. **Iterate until 0 unresolved** - Bots may add new reviews after fixes

<IMPORTANT>
PRs without evidence MUST remain in DRAFT. If evidence cannot be gathered:
1. Keep PR in draft status
2. Add "## Evidence" section explaining what's needed for manual verification
3. Add to Phase 4 action items under "🧪 QA Required (Human Verification)"
</IMPORTANT>

## Phase 4: Categorized Action Items

At the end of the workflow, ALWAYS provide a categorized summary:

```markdown
## 📋 Action Items Requiring Your Help

### 🧪 QA Required (Human Verification)
| PR | Why | Verification Steps |
|----|-----|-------------------|
| repo#123 | Windows-only fix | 1. Checkout branch 2. Run X on Windows 3. Verify Y |
| repo#456 | Needs API key | 1. Set API_KEY env 2. Run test suite 3. Check output |

### 🗣️ Manual Communication (Slack/Email)
| Item | Action Needed |
|------|---------------|
| ALL-1234 | Ping reviewer on Slack (PR stale >2 days) |
| ALL-5678 | Slack link needs manual review |

### 📝 Content/Social Media
| Item | Action Needed |
|------|---------------|
| ALL-2345 | Blog post requires writing |

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
- ALWAYS end with the categorized action items (Phase 4)
- Follow github-pr-workflow skill for ALL PR work
- For stale PRs, report direct links so user can ping reviewers
- Do NOT list reviews as "needing attention" - resolve them yourself
- Ask for confirmation before working on unclear tickets
</IMPORTANT>

---

## FAQ

### How do I run evaluations without local infrastructure?

Use the OpenHands CI system. See [eval-with-ci](../eval-with-ci/SKILL.md) skill.

**Quick method**: Add a label to a PR in `OpenHands/software-agent-sdk`:
- `run-eval-1` - 1 instance (sanity check)
- `run-eval-50` - 50 instances (standard)

**Manual dispatch**: Use the [Run Eval workflow](https://github.com/OpenHands/software-agent-sdk/actions/workflows/run-eval.yml) with custom parameters.

### What if I can't test a PR locally?

1. Keep the PR in **draft**
2. Add an `## Evidence` section explaining what's needed
3. Add to Phase 4 action items under "🧪 QA Required"
4. Include specific verification steps for the human

### How do I know which PRs need reviewer pings?

The agent checks all ready PRs and reports those >2 days old with direct links. The user then pings reviewers on Slack manually.

### How do I start Docker for testing?

If Docker is needed but the daemon isn't running, start it with:

```bash
sudo dockerd > /tmp/docker.log 2>&1 &
sleep 5
sudo docker ps  # Verify it's running
```

See the [docker skill](https://github.com/OpenHands/extensions/tree/main/skills/docker) for more details.
