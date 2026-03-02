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

## Quick Start

Run the fetch script to generate a structured checklist:

```bash
LINEAR_API_KEY="$LINEAR_API_KEY" GITHUB_TOKEN="$GITHUB_TOKEN" python workflow/scripts/daily-workflow-fetch.py --github-user neubig
```

> **Note**: The environment variables must be explicitly passed in the command to ensure they are properly injected from the secrets system.

This outputs a markdown checklist with:
- Linear tickets grouped by priority
- Ready PRs with staleness indicators (based on ready_for_review date, not creation date)
- Draft PRs grouped by action needed (🔴 fix CI, 🟡 gather evidence, 🟢 mark ready)

Then work through the checklist, taking action on each item.

## User Identifiers

- **Linear**: `graham@openhands.dev`
- **GitHub**: `neubig`

## Workflow Overview

The daily workflow consists of five phases executed in order:

```
0. PREPARATION        →  Read background skills before starting work
       ↓
1. LINEAR TICKETS     →  ACTUALLY WORK on highest priority first
       ↓
2. READY PRs          →  Check for reviews, move to draft if unresolved
       ↓  
3. DRAFT PRs          →  ACTUALLY FIX review feedback (don't just list it)
       ↓
4. ACTION ITEMS       →  ONLY items that truly require human help
```

## Phase 0: Preparation (Read First!)

<IMPORTANT>
**Before starting any work, read these background skills to understand the tools and processes:**

1. **[sub-agent-delegation](../sub-agent-delegation/SKILL.md)** - Learn how to parallelize work by delegating tasks to sub-agents. Essential for handling multiple PRs or tickets efficiently.

2. **[github-pr-workflow](../github-pr-workflow/SKILL.md)** - Complete PR handling instructions including:
   - Live testing requirements and evidence gathering
   - Review iteration loop (check → fix → resolve → repeat)
   - GraphQL commands for resolving review threads
   - When to mark PRs ready vs keep in draft

**Do not skip this phase.** Understanding delegation enables parallel work on multiple PRs. Understanding the PR workflow ensures you iterate correctly until all reviews are resolved.
</IMPORTANT>

<IMPORTANT>
**THIS IS AN ACTION-ORIENTED WORKFLOW, NOT A REPORTING WORKFLOW.**

- **DO NOT** just list tickets and PRs - actually work on them
- **DO NOT** report "this PR has review comments" - fix the comments yourself
- **DO NOT** add items to Phase 4 unless they genuinely require human intervention (credentials, platform access, manual QA, Slack communication)
- **DELEGATE** substantial tasks to sub-agents to parallelize work

The only items in Phase 4 should be things the agent literally cannot do:
- Ping someone on Slack (agent has no Slack access)
- Test on Windows (agent has no Windows machine)
- Use a specific API key (agent doesn't have the credential)
- Make org-level decisions (requires human judgment)
</IMPORTANT>

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

### For Each Ticket: TAKE ACTION

<IMPORTANT>
**ALWAYS attempt to work on every ticket. Never skip with "can investigate if desired".**

For each ticket:
1. Read the description fully
2. If it references code/repos, clone and investigate
3. If it's a bug, attempt to reproduce and fix it
4. If it's a feature, attempt to implement it
5. Only add to Phase 4 if you genuinely cannot proceed after trying
</IMPORTANT>

**Actionable (DO THE WORK):**
- Bug fixes with GitHub links → Clone repo, investigate, fix bug, open/update PR
- DataDog/monitoring errors → Investigate the codebase, find root cause, fix it
- Feature requests with clear specs → Implement the feature
- Investigation tasks → Actually investigate and report findings with conclusions
- Documentation tasks → Write the documentation

**Delegate to Sub-Agent:**
- If the ticket requires substantial work (>5 minutes), delegate it
- See [sub-agent-delegation](../sub-agent-delegation/SKILL.md)

**Add to Phase 4 ONLY if truly manual (after attempting work):**
- Tickets with only Slack links (no repo/code context)
- "Contact X" or "Send email to Y" tasks
- Discussion/meeting requests
- Org-level decisions requiring human judgment

## Phase 2: Ready PRs

### Fetch My Ready PRs

```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/search/issues?q=is:pr+is:open+author:neubig+draft:false" \
  | jq '.items[] | {repo: .repository_url | split("/") | .[-1], number: .number, title: .title}'
```

### Decision Tree

<IMPORTANT>
**Check ALL conditions for each Ready PR. Move to draft if ANY condition fails:**
1. Unresolved review comments
2. CI failures
3. Merge conflicts

Do NOT only check reviews - a PR with passing reviews but failing CI must also be moved to draft.
</IMPORTANT>

```
Ready PR
├── Has unresolved reviews? ─────────────────┐
│   └── YES → Move to draft                  │
├── Has CI failures? ────────────────────────┼─→ Process in Phase 3
│   └── YES → Move to draft                  │
├── Has merge conflicts (mergeable=false)? ──┘
│   └── YES → Move to draft
└── ALL conditions pass?
    └── YES → Ready for 2+ business days?
        └── YES → Check and report stale PRs (see below)
        └── NO → No action needed
```

### Batch Check All Conditions

```bash
# For each ready PR, check all conditions at once
for pr_info in "Owner/Repo/123"; do
  owner=$(echo $pr_info | cut -d'/' -f1)
  repo=$(echo $pr_info | cut -d'/' -f2)
  num=$(echo $pr_info | cut -d'/' -f3)
  
  # Check unresolved reviews
  unresolved=$(gh api graphql -f query="{ repository(owner: \"$owner\", name: \"$repo\") { pullRequest(number: $num) { reviewThreads(first: 50) { nodes { isResolved } } } } }" | jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length')
  
  # Check merge conflicts
  mergeable=$(gh api repos/$owner/$repo/pulls/$num --jq '.mergeable_state + " (" + (.mergeable | tostring) + ")"')
  
  # Check CI status
  ci_failures=$(gh pr checks $num --repo $owner/$repo 2>&1 | grep -c "fail\|error" || echo "0")
  
  echo "$owner/$repo#$num: reviews=$unresolved, mergeable=$mergeable, ci_failures=$ci_failures"
  
  # Move to draft if ANY condition fails
  if [ "$unresolved" != "0" ] || [ "$ci_failures" != "0" ] || echo "$mergeable" | grep -q "false"; then
    PR_ID=$(gh api repos/$owner/$repo/pulls/$num --jq '.node_id')
    gh api graphql -f query="mutation { convertPullRequestToDraft(input: {pullRequestId: \"$PR_ID\"}) { pullRequest { isDraft } } }"
    echo "  → Moved to draft"
  fi
done
```

### Check for Stale PRs

<IMPORTANT>
**Staleness is measured from when the PR became ready for review, NOT creation date.**

A PR that was created 47 days ago but only marked ready yesterday is NOT stale.
Check the timeline/events to find when the PR was last marked ready for review.
</IMPORTANT>

```bash
# For each ready PR, check when it was last marked ready
# Use the timeline API to find the 'ready_for_review' event
gh api repos/OWNER/REPO/issues/NUMBER/timeline --jq '
  [.[] | select(.event == "ready_for_review")] | last | .created_at'
```

A PR is stale if:
- It has been in ready state for >2 business days, AND
- Has no approving reviews

The agent will report:
> **Stale PRs (>2 days in ready state without review):**
> - https://github.com/org/repo/pull/123 - Fix bug (ready for 5 days)
>
> Please ping reviewers on Slack for these PRs.

## Phase 3: Draft PRs

### Fetch My Draft PRs

```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/search/issues?q=is:pr+is:open+author:neubig+draft:true" \
  | jq '.items[] | {repo: .repository_url | split("/") | .[-1], number: .number, title: .title}'
```

### For Each Draft PR: FIX AND MARK READY

<IMPORTANT>
**Follow the [github-pr-workflow](../github-pr-workflow/SKILL.md) skill for each draft PR.**

That skill covers:
- Fixing failing CI/tests (don't just report them - fix them)
- Gathering evidence for bug fixes and features
- Iterating on review comments until resolved
- When to mark ready vs keep in draft

**Key principle**: A PR should be marked ready only when BOTH conditions are met:
1. Evidence exists (or it's content-only)
2. No unresolved review threads
</IMPORTANT>

### Parallelization

If there are multiple draft PRs needing work:
1. Check if DelegateTool is available in your tool set, OR
2. Check if `OPENHANDS_CLOUD_API_KEY` environment variable is set
3. If either is available, delegate each PR to a sub-agent (see [sub-agent-delegation](../sub-agent-delegation/SKILL.md))
4. If neither is available, work through PRs sequentially (note this in the summary)

### When to Add to Phase 4 (Rare Cases Only)

PRs remain in DRAFT **only if** evidence cannot be gathered due to:
- Missing credentials the agent doesn't have
- Platform-specific testing (Windows, macOS) the agent can't do
- External service access the agent lacks

In these cases: keep PR in draft, add "## Evidence" section explaining what's needed, and add to Phase 4.

## Phase 4: Complete Status Summary

<IMPORTANT>
**EVERY PR and Linear ticket examined MUST appear in the final summary.**
This is not optional - the user needs a complete picture of their work items.
</IMPORTANT>

At the end of the workflow, ALWAYS provide a **complete status summary** with two sections:

### Section 1: All Items Status

List EVERY item examined with its current status. **Include a link to each item.**

```markdown
## 📊 Complete Status Summary

### Linear Tickets
| Ticket | Title | Status | Action Taken / Needed |
|--------|-------|--------|----------------------|
| [ALL-1234](https://linear.app/all-hands/issue/ALL-1234) | Fix bug X | ✅ Resolved | Opened PR #123 |
| [ALL-5678](https://linear.app/all-hands/issue/ALL-5678) | Contact Y | 🔶 Manual | Requires Slack outreach |
| [PLTF-99](https://linear.app/all-hands/issue/PLTF-99) | Migrate Z | 🔶 Manual | Needs org admin decision |

### Ready PRs
| PR | Title | Status | Action Taken / Needed |
|----|-------|--------|----------------------|
| [repo#123](https://github.com/org/repo/pull/123) | Fix bug | ✅ Merged | Approved and merged |
| [repo#456](https://github.com/org/repo/pull/456) | Add feature | ✅ Ready | All reviews resolved |
| [repo#789](https://github.com/org/repo/pull/789) | Update docs | 🔶 Stale | Needs reviewer ping on Slack |

### Draft PRs  
| PR | Title | Status | Action Taken / Needed |
|----|-------|--------|----------------------|
| [repo#111](https://github.com/org/repo/pull/111) | Refactor | ✅ Fixed | Addressed feedback, marked ready |
| [repo#222](https://github.com/org/repo/pull/222) | New API | 🔶 Blocked | Needs Windows testing |
```

### Section 2: Items Requiring Human Help

Only items the agent literally cannot do. **Include links.**

```markdown
## 📋 Action Items Requiring Your Help

### 🗣️ Manual Communication (Slack/Email)
| Item | Action Needed |
|------|---------------|
| [repo#789](https://github.com/org/repo/pull/789) | Ping reviewer on Slack (stale >2 days) |

### 🖥️ Platform / Environment Access
| PR | Resource Needed |
|----|-----------------|
| [repo#222](https://github.com/org/repo/pull/222) | Windows machine for testing |

### 🔑 Credentials / API Keys Needed
| PR | Resource Needed |
|----|-----------------|
| [repo#333](https://github.com/org/repo/pull/333) | API key for service X |

### ❓ Decisions / Clarification Needed
| Item | Question |
|------|----------|
| [PLTF-99](https://linear.app/all-hands/issue/PLTF-99) | Requires org admin decision on migration |
```

After the summary, confirm:
> I have taken action on all items where I could. The items above are the only ones requiring your help.

## Important Notes

<IMPORTANT>
- ALWAYS end with the categorized action items (Phase 4)
- Follow github-pr-workflow skill for ALL PR work
- For stale PRs, report direct links so user can ping reviewers
- Do NOT list reviews as "needing attention" - resolve them yourself
- Ask for confirmation before working on unclear tickets
- **Delegate substantial tasks**: If a ticket or PR involves work that would take several minutes or more and is self-contained (e.g., refactoring a module, running extensive tests, researching across repos), use [sub-agent-delegation](../sub-agent-delegation/SKILL.md) to parallelize work
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

### How do I investigate Datadog errors or monitoring issues?

The agent has Datadog access via environment variables (`DD_API_KEY`, `DD_APP_KEY`, `DD_SITE`). Linear tickets about Datadog errors or monitoring issues should be investigated directly - do NOT add them to Phase 4 as "requiring access".

See the [datadog skill](https://github.com/OpenHands/extensions/tree/main/skills/datadog) for canonical instructions on:
- Querying logs
- Querying metrics
- Querying APM traces
- Listing monitors

**Example**: Query recent errors:
```bash
curl -s -X POST "https://api.${DD_SITE}/api/v2/logs/events/search" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "query": "status:error",
      "from": "now-1h",
      "to": "now"
    },
    "sort": "-timestamp",
    "page": {"limit": 50}
  }' | jq .
```
