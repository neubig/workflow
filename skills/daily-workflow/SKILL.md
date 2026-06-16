---
name: daily-workflow
description: Graham's human-in-the-loop daily workflow for checking PRs awaiting review, then aligning open GitHub PRs, GitHub issues, Linear tickets, and recent Slack requests before choosing development work.
triggers:
- daily workflow
- my workflow
- graham workflow
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
- Do not start implementation work during this workflow unless Graham explicitly asks for it after the status pass.

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

Before walking the priority queue, fetch Graham's incomplete, unblocked assigned Linear tickets with priority `0 No priority`.

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

For each ticket, report:
1. **Open PR?** Link the PR if one exists. If none exists, say `No`.
2. **CI status:** passing, failing, pending, missing, or unknown.
3. **Review status:** passing review, changes requested/unresolved comments, awaiting review, or unknown.
4. **Live-code evidence:** whether the PR shows evidence that live code failed before and passed after. For non-bug work, evidence should show the live feature or workflow running successfully.
5. **If no PR is open:** the additional context, credentials, repository access, environment, or decision needed to start work. If nothing is missing, say what repo/task context is enough to start.

Do not mark a ticket as ready based only on unit tests. Live-code evidence is required unless the PR is truly content-only.

After providing the final summary tables, continue into an interactive Linear ticket walkthrough. Walk the sorted, unblocked Linear tickets one by one, starting with the highest-priority ticket. For each ticket:
1. Give Graham a concise summary of the ticket, current state, linked GitHub work, CI/review/evidence status, and what appears to be blocked or ready.
2. Ask Graham what the next action should be before moving to the next ticket.
3. Do not start implementation, mutate Linear, close tickets, or skip ahead unless Graham explicitly chooses that action.
4. If Graham asks to skip a ticket, move to the next ticket in priority order and keep the skipped ticket in the final action list.
5. If Linear access is unavailable, do not attempt the interactive walkthrough; instead report the missing Linear access needed to fetch assigned tickets.

## Final Output

End with these sections:

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
