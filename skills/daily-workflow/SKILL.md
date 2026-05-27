---
name: daily-workflow
description: Graham's daily workflow for managing Linear tickets and GitHub PRs. Prioritizes work by Linear priority, manages PR review cycles, and tracks resources needed for testing.
triggers:
- daily workflow
- my workflow
- graham workflow
---

# Graham's Daily Workflow

Use this skill to execute Graham's daily work, not merely plan or report on it. It gathers assigned Linear tickets and GitHub PRs, prioritizes them, does agent-actionable work directly, delegates larger independent tasks, and reserves the final action list for true human blockers.

## Start Here

Begin by building a complete picture of the work queue. Linear is the source for assigned tickets and priorities; GitHub is the source for PR status, reviews, CI, and evidence. Use Linear MCP tools for ticket triage, then use the fetch script for GitHub PR triage only:

```bash
GITHUB_TOKEN="$GITHUB_TOKEN" python workflow/scripts/daily-workflow-fetch.py --github-user neubig --skip-linear
```

Pass `GITHUB_TOKEN` explicitly so secret injection works. The script output groups ready PRs with staleness based on ready-for-review time and draft PRs by action: 🔴 fix CI, 🟡 gather evidence, 🟢 mark ready.

Before acting, read:
- [sub-agent-delegation](../sub-agent-delegation/SKILL.md): delegate self-contained work >5 minutes.
- [iterate](https://github.com/OpenHands/extensions/tree/main/skills/iterate): drive GitHub PRs through CI, review, and QA until merge-ready.

## Core Rules

- This is for action, not reporting: work tickets/PRs; do not merely list them.
- Resolve review comments yourself; do not report them as needing attention.
- Delegate substantial independent tickets/PRs.
- Phase 4 is only for things the agent literally cannot do: Slack/email outreach, Windows or other unavailable platform testing, missing credentials/API keys, external-service access, or org-level decisions.
- Every examined Linear ticket and PR must appear in the final summary with a link.

## Phase 1: Linear Tickets

Use Linear MCP tools; do not call the Linear API directly. Fetch assigned, incomplete tickets with `list_issues` using `assignee: "me"` and excluding completed/canceled states. Use `get_issue` for full descriptions, labels, blockers, comments, attachments, and linked GitHub context.

Priority: `1 Urgent` → now, `2 High` → first, `3 Medium` → after high, `4 Low` → later.

For every ticket:
1. Read it fully.
2. Exclude if blocked by another active issue or labeled `Blocked`.
3. If it links to an active GitHub issue/PR, treat GitHub as source of truth and surface the direct link, not duplicate Linear-only work.
4. If code/repo context exists and no active GitHub work exists, clone/investigate.
5. Reproduce/fix bugs, implement clear features, investigate monitoring/DataDog errors, write docs.
6. Add to Phase 4 only after trying and finding a real manual blocker.

Manual-only examples: Slack-only context, “contact/send email” tasks, meeting/discussion requests, org decisions.

## Phase 2: Ready PRs

For each ready PR, use the [iterate skill](https://github.com/OpenHands/extensions/tree/main/skills/iterate) rather than duplicating PR-specific instructions here. Drive the PR through the verification layers that exist for that repo, fix issues directly, and only report stale/blocked PRs when human help is actually needed.

## Phase 3: Draft PRs

Use the [iterate skill](https://github.com/OpenHands/extensions/tree/main/skills/iterate) for draft PRs as well. Delegate multiple/substantial PRs, and keep only genuine human blockers in Phase 4.

## Phase 4: Final Summary

Always end with both sections below.

```markdown
## 📊 Complete Status Summary

### Linear Tickets
| Ticket | Title | Status | Action Taken / Needed |
|--------|-------|--------|----------------------|
| [ALL-1234](https://linear.app/all-hands/issue/ALL-1234) | Fix bug X | ✅ Resolved | Opened PR #123 |
| [ALL-5678](https://linear.app/all-hands/issue/ALL-5678) | Contact Y | 🔶 Manual | Requires Slack outreach |

### Ready PRs
| PR | Title | Status | Action Taken / Needed |
|----|-------|--------|----------------------|
| [repo#123](https://github.com/org/repo/pull/123) | Fix bug | ✅ Merged | Approved and merged |
| [repo#789](https://github.com/org/repo/pull/789) | Update docs | 🔶 Stale | Needs reviewer ping on Slack |

### Draft PRs
| PR | Title | Status | Action Taken / Needed |
|----|-------|--------|----------------------|
| [repo#111](https://github.com/org/repo/pull/111) | Refactor | ✅ Fixed | Addressed feedback, marked ready |
| [repo#222](https://github.com/org/repo/pull/222) | New API | 🔶 Blocked | Needs Windows testing |

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

Then say: “I have taken action on all items where I could. The items above are the only ones requiring your help.”

## Quick References

- No access without credentials/API keys; commonly manual: Slack messaging, Notion OAuth, Figma OAuth.
- Evaluations: [eval-with-ci](../eval-with-ci/SKILL.md).
- PR iteration: [iterate skill](https://github.com/OpenHands/extensions/tree/main/skills/iterate).
- Docker testing: [docker skill](https://github.com/OpenHands/extensions/tree/main/skills/docker).
- DataDog: [datadog skill](https://github.com/OpenHands/extensions/tree/main/skills/datadog); env vars are `DD_API_KEY`, `DD_APP_KEY`, `DD_SITE`.
