---
name: update-todos
description: Cross-platform work reconciliation. Scans Slack commitments, GitHub issues/PRs, and Linear tickets to find gaps, create missing tracking items, and ensure everything is consistent and up to date.
triggers:
- update todos
- update my todos
- reconcile work items
- sync linear github slack
- are my issues up to date
- organize my work
- what am I working on
---

# Update Todos

Reconcile a user's work items across Slack, GitHub, and Linear. Identifies gaps where work is happening but not tracked, flags stale items, and fills in missing tracking artifacts.

## Workflow Overview

```
1. IDENTIFY USER        →  Resolve the user across Slack, GitHub, Linear
       ↓
2. GATHER               →  Slack commitments + GitHub issues/PRs + Linear tickets
       ↓
3. CROSS-REFERENCE      →  Find gaps (untracked PRs, missing issues, stale items)
       ↓
4. FILL GAPS            →  Create issues, link PRs, update Linear (with permission)
       ↓
5. FLAG FOR REVIEW      →  Surface stale/overdue items for user decision
       ↓
6. CLOSE THE LOOP       →  Follow up on outstanding Slack commitments
```

## Phase 1: Identify the User

Before doing anything, resolve the user's identity on all three platforms.

- **Slack**: Use `slack_read_user_profile` (defaults to current user) or `slack_search_users` to get the user ID.
- **GitHub**: Use `gh api /user` or ask the user for their GitHub username. Confirm by checking recent activity.
- **Linear**: Use `linear__get_user` with `"me"` or search by name/email. Extract the Linear user UUID for filtering.

Store these identifiers — you'll need them for every subsequent query.

## Phase 2: Gather Work Items

Collect from all three sources in parallel where possible.

### Slack Commitments

Search for messages where the user made commitments. Use multiple targeted queries:

```
from:@username "I'll"
from:@username "I will"
from:@username "going to"
from:@username "plan to"
from:@username "TODO"
from:@username "action item"
from:@username "follow up"
from:@username "get back to"
from:@username "take a look"
from:@username "I can do"
from:@username "I'll handle"
```

**Time range**: Focus on the last 30 days by default. Use `after:YYYY-MM-DD` to filter. Go further back if the user asks.

**Read threads**: For each hit, read the surrounding thread with `slack_read_thread` to understand context. A message like "I'll look into it" might already be resolved later in the same thread.

### GitHub Issues

Query across all relevant organizations/repos:

```bash
gh issue list --assignee USERNAME --state open --json number,title,repository,createdAt,updatedAt --limit 100
```

For multi-org users, repeat for each org. Common patterns:
- `gh search issues --assignee=USERNAME --state=open`
- Check repos the user has recently pushed to: `gh api "/users/USERNAME/events" | jq '[.[].repo.name] | unique'`

### GitHub PRs

```bash
gh search prs --author=USERNAME --state=open --json number,title,repository,createdAt,updatedAt,isDraft,reviewDecision
```

This is critical — PRs represent actual in-flight work and are the most reliable signal of what someone is actively doing.

### Linear Issues

Use Linear MCP tools to get all open issues:

- `list_issues` with `assignee: "me"`, `state: "started"` → In Progress items
- `list_issues` with `assignee: "me"`, `state: "unstarted"` → Todo items
- `list_issues` with `assignee: "me"`, `state: "backlog"` → Backlog items

## Phase 3: Cross-Reference

This is the core of the skill. Build a mental map connecting items across platforms.

### Rule: Every open PR should have at least one GitHub issue

For each open PR, check:
1. Does the PR body reference an issue? (Look for `Fixes #N`, `Closes #N`, `Resolves #N`, or a link like `org/repo#N`)
2. Is there a GitHub issue that mentions this PR?

If not, this is a gap that needs to be filled in Phase 4.

**Multi-repo PRs**: When the same logical change spans multiple repos (e.g., SDK + app + infra), create ONE issue on the primary repo and have all PRs reference it.

### Rule: GitHub issues should be tracked in Linear

If the GitHub-to-Linear integration is configured, issues auto-ingest. Verify by searching Linear for the issue title or GitHub URL. If issues aren't auto-ingesting, flag this for the user.

### Rule: Active work should be In Progress in Linear

If a PR is open and the corresponding Linear issue exists but is in Backlog/Todo/Triage, the Linear issue should be moved to In Progress.

### Rule: Slack commitments should be trackable

For each Slack commitment found, check:
1. Is there a corresponding GitHub issue or PR?
2. Is there a Linear ticket?
3. Was it resolved later in the same thread?

If a commitment is untracked and still relevant, flag it.

### Staleness Detection

Flag items that appear stale:
- **In Progress Linear issues** with no activity for 30+ days
- **Todo items** that are 60+ days old with no updates
- **PRs** that are approved but not merged for 14+ days
- **Issues** with overdue due dates

## Phase 4: Fill Gaps

<IMPORTANT>
**Permission rules — strictly follow these:**
- ✅ You CAN create GitHub issues (low risk, easily closeable)
- ✅ You CAN edit PR descriptions to add issue references
- ✅ You CAN update Linear issue status and priority (with user's approval of MCP access)
- ✅ You CAN set priorities on newly created items
- ❌ You MUST NOT cancel, close, or archive any ticket without explicit user permission
- ❌ You MUST NOT merge PRs
- ❌ You MUST NOT change assignees on items you didn't create
</IMPORTANT>

### Creating GitHub Issues for Untracked PRs

For each PR that lacks an issue:

1. Write a clear issue title matching the PR's intent
2. Include a Summary section describing the change
3. Include a Related PRs section listing all PRs for this work item
4. Include a Details section with bullet points on what changes
5. Add attribution: `_This issue was created by an AI agent (OpenHands) on behalf of [User]._`
6. Assign the issue to the user
7. Update the PR body to reference the new issue with `Resolves #N`

Use `gh issue create` and `gh pr edit` for this.

### Updating Linear Issues

For Linear issues that correspond to active PRs:

1. Set status to **In Progress**
2. Ensure assigned to the correct user
3. Set priority based on context:
   - **Urgent (1)**: Production incidents, security fixes
   - **High (2)**: Partner/customer commitments, bug fixes, cross-cutting infrastructure (e.g., dependency upgrades across repos)
   - **Medium (3)**: Feature work, integrations, tooling improvements
   - **Low (4)**: Nice-to-haves, cosmetic changes, exploration tasks

### Linking

After creating issues and updating PRs:
- Verify that new GitHub issues auto-ingest to Linear (may take a few minutes)
- Confirm the Linear issues appear and are linked to the right GitHub issues

## Phase 5: Flag for Review

Present the user with items that need their decision. Do NOT take action on these — only report.

Format as a table:

```
### ⚠️ Items Needing Your Attention

| Issue | Age | Problem | Suggested Action |
|-------|-----|---------|-----------------|
| ALL-1234 | 90 days | In Progress but no activity since Feb | Move to Todo or close? |
| ALL-5678 | 45 days | Todo, due date was Mar 1 | Still relevant? |
| PR #123 | 30 days | Approved but not merged | Merge or close? |
```

Let the user decide. If they give permission to cancel/close items, do it. Otherwise leave them alone.

## Phase 6: Close the Loop on Slack

For Slack commitments that are untracked and appear unresolved:

1. **If the commitment has a corresponding Linear ticket or GitHub issue** → Note that it's covered, no action needed.
2. **If the commitment is untracked but still seems relevant** → Ask the user if they want a Linear ticket created.
3. **If the commitment appears stale** (old, no thread follow-up) → Ask the user if they want to post a follow-up message in the thread. Draft the message for their approval before sending.

When posting follow-up messages in Slack threads:
- Be honest and lightweight: "Circling back on this — did we follow up or is this stale?"
- Always tag the relevant people from the original thread
- Always include the AI attribution note

## Output Summary

At the end of the workflow, provide a structured summary:

```
### ✅ Completed
- Created N GitHub issues for untracked PRs
- Linked N PRs to their issues
- Updated N Linear issues to In Progress with priorities
- Followed up on N stale Slack commitments

### ⚠️ Flagged for Your Decision
- N stale In Progress items (list them)
- N overdue Todo items (list them)
- N untracked Slack commitments (list them)

### 📊 Current State
- N open PRs across N repos, all tracked
- N Linear issues In Progress
- N Linear issues in Todo
```

## Tips

- **Work across all repos**: Don't just check the main repo. Users often have PRs across 5+ repos for the same org.
- **Check PR review status**: PRs that are approved but unmerged are action items. PRs with requested changes need follow-up.
- **Batch API calls**: Use parallel tool calls where possible (e.g., query GitHub and Linear simultaneously).
- **Don't over-create**: If a Slack commitment is vague ("I should look into X someday"), it doesn't need a ticket. Only track concrete commitments.
- **Respect the user's system**: Some people use Linear for everything, others use it loosely. Match their existing patterns rather than imposing rigid structure.
