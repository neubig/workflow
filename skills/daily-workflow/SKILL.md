---
name: daily-workflow
description: Graham's human-in-the-loop daily workflow ("daily workflow", "my workflow", or "Graham workflow") for checking PRs awaiting review, aligning open GitHub PRs, GitHub issues, Linear tickets, and recent Slack requests, then remediating authored PRs with conflicts, failing CI, unresolved review threads, or missing live evidence.
---

# Graham's Daily Workflow

Use this skill when Graham asks for the daily workflow. The goal is to make the work queue coherent before doing implementation work: PRs waiting for Graham's review should be checked first, every open PR should have a GitHub issue, every relevant issue should be assigned to Graham and tracked in Linear, Slack-derived work should be proposed for confirmation, and Linear tickets should be reviewed in priority order with concrete readiness status.

## Operating Rules

- Be human-in-the-loop. Propose new GitHub issues or Linear tickets before creating them from Slack messages or ambiguous context.
- Prefer Linear MCP tools for Linear reads/writes. If Linear tools are unavailable, say so and ask for access rather than documenting raw API workarounds.
- Prefer GitHub tools or `gh` for GitHub reads/writes.
- Check Slack only when a Slack connector/tool is available. If unavailable, report that Slack intake could not be checked.
- Make assignment explicit: associated GitHub issues and Linear tickets should be assigned to Graham.
- Omit blocked Linear issues from the status tables and interactive walkthrough. Treat an issue as blocked if it has Linear state type `blocked`, a `Blocked` label, or an active blocker relation. Do not mention blocked issues unless Graham explicitly asks for blocked work.
- When sharing the next workflow step, include the relevant Linear or GitHub link if there is one.
- Do not start PR remediation until the initial status report has been shown to Graham. After that report, remediation of eligible Graham-authored PRs is part of the daily workflow and does not require a second request. Keep unrelated implementation work human-in-the-loop.

## Step 1: Check PRs Waiting For Graham's Review

Find open PRs where Graham has been requested as a reviewer:

```bash
gh search prs --review-requested=@me --state=open --json repository,number,title,url,isDraft,author,updatedAt
```

If `@me` is unavailable in the current environment, use `--review-requested=neubig`. If GitHub search does not support the review-requested query, use GitHub tools or GraphQL to find open PRs with `neubig` or Graham's teams in the requested reviewer list.

For each PR:
1. Read the PR summary, changed files, CI status, review decision, and recent discussion. Use `gh pr view` or GitHub tools for details that `gh search prs` does not return.
2. Classify it as `Ready for Graham review`, `Draft/not ready`, `Blocked by CI`, `Needs author response`, or `Already handled/stale request`.
3. Put PRs that are genuinely ready for Graham review before other workflow items.
4. Do not perform the review or approve/request changes unless Graham explicitly asks for that action.

## Step 2: Inventory Open PRs and Their Issues

Find all open PRs authored by `neubig`:

```bash
gh search prs --author neubig --state open --json repository,number,title,url,isDraft
```

For each PR:
1. Read the PR body, timeline, linked issues, closing keywords, and development links.
2. Determine whether it is associated with at least one GitHub issue.
3. Record each associated issue and whether it is assigned to Graham.

If a PR has no associated issue:
1. Search for related issues in the same repository using title keywords, branch names, and PR body terms.
2. If a related issue exists, associate it with the PR by adding a clear issue link or closing keyword to the PR body, depending on whether the PR should close the issue.
3. If no related issue exists, create a concise GitHub issue in the same repository, assign it to Graham, and associate the PR with it.

Only create a GitHub issue without asking Graham when the PR itself provides unambiguous code context. If the context is unclear, propose the issue title/body first.

## Step 3: Ensure GitHub Issues Are Assigned

For every issue associated with Graham's open PRs:
1. Check the issue assignees.
2. Assign the issue to `neubig` if Graham is not already assigned and the repository permits it.
3. If assignment fails because of permissions or repository rules, include that issue in the final action list.

## Step 4: Ensure Linear Tracking

For every associated GitHub issue:
1. Check whether it has been ingested into Linear.
2. If a matching Linear ticket exists, verify it is assigned to Graham.
3. If the Linear ticket is unassigned or assigned to someone else, assign it to Graham unless there is clear evidence that another owner is intentional.
4. If no Linear ticket exists, create or request ingestion according to the available Linear/GitHub integration tooling, then assign the resulting ticket to Graham.

If Linear tools are unavailable, continue the rest of the workflow and list the exact Linear checks that could not be completed.

## Step 5: Slack Intake

Check recent Slack messages directed to Graham and recent threads where Graham participated. Look for requests that imply follow-up work.

Classify each candidate:

| Candidate | Create In | Criteria |
|-----------|-----------|----------|
| Code work | GitHub issue | Bug, feature, repo-specific investigation, failing code, docs/code change |
| Non-code work | Linear ticket | Planning, coordination, customer follow-up, process, research, decision tracking |
| No ticket | None | FYI, already tracked, social/status-only, too ambiguous |

For every candidate, propose:
- source Slack channel/thread link
- proposed destination: GitHub issue or Linear ticket
- title
- short body
- assignee
- reason it should be tracked

Ask Graham to confirm before creating any Slack-derived GitHub issue or Linear ticket.

## Step 6: Prioritize Unprioritized Linear Tickets

Before walking the priority queue, fetch Graham's incomplete, unblocked assigned Linear tickets with priority `0 No priority`. Use the query method described in [Fetching Incomplete Linear Tickets](#fetching-incomplete-linear-tickets) to exclude completed, canceled, and duplicate tickets at the API level rather than paginating through all assigned issues.

When active unprioritized tickets exist:
1. Exclude completed, canceled, duplicate, archived, and blocked tickets.
2. Inspect linked GitHub PRs/issues when available so merged/stale trackers can be closed or marked duplicate instead of prioritized.
3. Suggest priorities for all active unprioritized tickets at once, grouped as `High`, `Medium`, `Low`, and `Close/Duplicate`.
4. Base the recommendation on whether the ticket blocks other roadmap work or other people, has an explicit deadline or SLA risk, affects a core offering versus auxiliary polish, is customer/admin/security sensitive, or is only a tracker/cleanup item.
5. Ask Graham for corrections before mutating Linear. If Graham approves, apply the priority/state changes and then continue the workflow.

## Step 7: Walk Linear Tickets by Priority

Fetch Graham's incomplete, unblocked assigned Linear tickets and sort by priority:
`1 Urgent`, `2 High`, `3 Medium`, `4 Low`, `0 No priority`.

When using Linear MCP tools, do not rely on unsupported shorthand filters such as `state=uncompleted`. Either request Graham's assigned issues and filter locally, or use an explicit state/type filter that excludes completed, canceled, duplicate, and blocked work. Also exclude tickets with a `Blocked` label or an active blocker relation before building the table or starting the walkthrough.

### Fetching Incomplete Linear Tickets

The Linear MCP `list_issues` tool does not support excluding state types (e.g., "not completed"). To avoid paginating through hundreds of completed/canceled issues, use the Linear GraphQL API directly with a `nin` (not-in) filter on `state.type`:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "query { viewer { assignedIssues(first: 250, filter: { state: { type: { nin: [\"completed\", \"canceled\", \"duplicate\"] } } }) { nodes { id identifier title priority priorityLabel state { name type } labels { nodes { name } } url createdAt updatedAt dueDate } } } }"
  }' | jq '.data.viewer.assignedIssues.nodes'
```

This returns only incomplete tickets (backlog, unstarted, started, and triage states). After receiving the results, additionally filter out:
- Tickets with a `Blocked` label
- Tickets with an active blocker relation (check `blockedBy` if available)
- Archived tickets

If `LINEAR_API_KEY` is not set, fall back to the MCP `list_issues` tool with `assignee=me` and filter locally, paginating through all results. This is less efficient but functional.

If neither the GraphQL API nor MCP tools are available, report that Linear issues could not be fetched and list the exact access needed.

For each ticket, report:
1. **Open PR?** Link the PR if one exists. If none exists, say `No`.
2. **CI status:** passing, failing, pending, missing, or unknown.
3. **Review status:** passing review, changes requested/unresolved comments, awaiting review, or unknown.
4. **Live-code evidence:** whether the PR shows evidence that live code failed before and passed after. For non-bug work, evidence should show the live feature or workflow running successfully.
5. **If no PR is open:** the additional context, credentials, repository access, environment, or decision needed to start work. If nothing is missing, say what repo/task context is enough to start.

Do not mark a ticket as ready based only on unit tests. Live-code evidence is required unless the PR is truly content-only.

## Step 8: Remediate Open PRs After the Initial Report

Show Graham the initial status tables in [Initial Status Output](#initial-status-output) before changing PR code. Treat this as an interim report and continue the same turn.

Then revisit every open PR authored by `neubig` from Step 2. A PR is eligible for remediation when any of these conditions apply:

1. GitHub reports merge conflicts or the branch cannot merge cleanly.
2. One or more required CI checks are failing.
3. An actionable review thread remains unresolved. Use thread-level GitHub data, not only flat comments, so resolved and outdated threads are distinguished correctly.
4. The PR lacks genuine live-code evidence. Unit tests alone do not count; exempt only work that is truly content-only.

For every eligible PR:

1. Re-read the current PR head, checks and logs, merge state, changed files, repository instructions, and unresolved review threads immediately before working.
2. Work on the existing PR head branch. Do not force-push, open a replacement PR, merge, approve, or close the PR.
3. Resolve conflicts without discarding unrelated branch work. Fix failing checks at their observed root cause. Address actionable review feedback and mark a thread resolved only after its requested change is complete.
4. Exercise the changed production code through a real process, endpoint, CLI, browser, database, MCP server, rendered deployment, or similarly honest path. Capture the exact setup, commands, and observations. Never fabricate evidence or call unit tests live evidence.
5. Commit and push focused changes to the existing branch, then update the PR body with a concise `## Live evidence` section. Preserve the unchecked human-testing checkbox.
6. Recheck GitHub after pushing and record current mergeability, CI, unresolved-thread status, evidence, commit SHA, and any exact blocker.

When several PRs are eligible, prefer separate OpenHands or Agent Canvas conversations per PR when that environment is available. Keep each prompt self-contained, limit concurrency to what the backend can safely support, monitor every conversation to a terminal state, and independently verify its GitHub result. If delegated conversations are unavailable, work through the PRs sequentially in priority order: merge conflicts, failing CI, unresolved review threads, then missing live evidence.

Do not modify PRs authored by other people merely because they appeared in Step 1 as awaiting Graham's review. If credentials, repository access, external services, or reproducible live environments block a fix, exhaust safe alternatives and report the precise blocker instead of claiming success.

After all eligible PRs have been attempted, emit the [PR Remediation Output](#pr-remediation-output), then continue to Step 9.

## Step 9: Interactive Linear Ticket Walkthrough

Walk the sorted, unblocked Linear tickets one by one, starting with the highest-priority ticket. For each ticket:
1. Give Graham a concise summary of the ticket, current state, linked GitHub work, CI/review/evidence status, and what appears to be blocked or ready.
2. Ask Graham what the next action should be before moving to the next ticket.
3. Do not start implementation, mutate Linear, close tickets, or skip ahead unless Graham explicitly chooses that action.
4. If Graham asks to skip a ticket, move to the next ticket in priority order and keep the skipped ticket in the final action list.
5. If Linear access is unavailable, do not attempt the interactive walkthrough; instead report the missing Linear access needed to fetch assigned tickets.

## Initial Status Output

Before Step 8 changes PR code, show these sections:

```markdown
## PRs Awaiting Graham Review

| PR | Author | CI | Review Status | Action |
|----|--------|----|---------------|--------|

## PR Issue Alignment

| PR | Associated Issue | Issue Assigned To Graham | Linear Tracked | Action |
|----|------------------|--------------------------|----------------|--------|

## Slack Proposals

| Source | Proposed Ticket | Destination | Reason | Awaiting Confirmation |
|--------|-----------------|-------------|--------|-----------------------|

## Linear Priority Walkthrough

| Linear | Priority | Open PR | CI | Review | Live Evidence | Context Needed |
|--------|----------|---------|----|--------|---------------|----------------|

## Action Items Requiring Graham

| Item | Needed |
|------|--------|
```

If a tool or credential was missing, include it in `Action Items Requiring Graham` with the exact access needed.

## PR Remediation Output

After Step 8, report every eligible PR, including unsuccessful attempts:

```markdown
## PR Remediation Results

| PR | Conversation | Merge Conflicts | CI | Unresolved Review Threads | Live Evidence | Commit / PR Update | Remaining Blocker |
|----|--------------|-----------------|----|---------------------------|---------------|--------------------|-------------------|
```

Link each delegated conversation when one was used. Distinguish `fixed`, `still failing`, `pending`, and `blocked` rather than collapsing them into a generic completion state. Re-fetch GitHub immediately before producing this table.
