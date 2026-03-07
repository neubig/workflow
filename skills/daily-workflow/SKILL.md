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

**Use the [github-pr-workflow](../github-pr-workflow/SKILL.md) skill for all PR operations.**

For each ready PR, check the PR Readiness Checklist. If ANY condition fails, move to draft and process in Phase 3.

### Stale PR Detection

PRs are stale if in ready state for >2 business days without approving reviews.

<IMPORTANT>
**Staleness is measured from when the PR became ready for review, NOT creation date.**
</IMPORTANT>

```bash
# Check when PR was last marked ready
gh api repos/OWNER/REPO/issues/NUMBER/timeline --jq '
  [.[] | select(.event == "ready_for_review")] | last | .created_at'
```

Report stale PRs for human follow-up (Slack ping).

## Phase 3: Draft PRs

**Follow the [github-pr-workflow](../github-pr-workflow/SKILL.md) skill for each draft PR.**

That skill covers the complete PR Readiness Checklist including:
- Evidence requirements (END-TO-END, not unit tests)
- Review iteration loop
- Code quality checks
- All GraphQL commands needed

### Parallelization

For multiple draft PRs, delegate to sub-agents. See [sub-agent-delegation](../sub-agent-delegation/SKILL.md).

### When to Add to Phase 4

PRs remain in DRAFT if live evidence cannot be gathered due to missing credentials, platform requirements, or external service access. Do not move them to ready-for-review based only on CI, unit tests, or a written summary. Add an `## Evidence` section that says what you tried, what blocked live verification, and the exact manual verification steps a human should run.

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

All items the agent cannot do. Do NOT include items that simply have issues like failing CI, these should be fixed by the agent.

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

### What services can you not access?

If you do not have an API key or credential for a service, you cannot access it. This includes:
- Slack (no messaging access)
- Notion (no access to Notion MCP due to OAuth)
- Figma (no access to Figma MCP due to OAuth)

For these you will need to ask for human help.

### How do I run evaluations without local infrastructure?

Use the OpenHands CI system. See [eval-with-ci](../eval-with-ci/SKILL.md) for the supported `run-eval-*` labels, workflow dispatch options, and monitoring steps.

### What if I can't test a PR locally?

See "When Evidence Truly Cannot Be Gathered" in [github-pr-workflow](../github-pr-workflow/SKILL.md).

### How do I start Docker for testing?

See the [docker skill](https://github.com/OpenHands/extensions/tree/main/skills/docker).

### How do I investigate Datadog errors?

See the [datadog skill](https://github.com/OpenHands/extensions/tree/main/skills/datadog). The agent has Datadog access via `DD_API_KEY`, `DD_APP_KEY`, `DD_SITE`.
