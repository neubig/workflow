---
name: daily-workflow
description: Human-in-the-loop daily workflow ("daily workflow", "my workflow", or "work queue") for checking review requests, aligning GitHub PRs and issues with Linear tickets, and triaging recent Slack requests before remediating the current user's eligible PRs.
---

# Daily Workflow

Use this skill when the user asks to review or organize their daily workflow. The goal is to make the user's work queue coherent before implementation: review requests come first, active PRs have appropriate GitHub issue and Linear tracking, Slack-derived work is proposed for confirmation, and active Linear tickets are reviewed in priority order.

## Operating Rules

- Resolve the current user before taking action. Use `gh api user --jq .login` for GitHub, the current-user identity from Linear, and the current Slack profile when those services are available. Ask the user when an identity cannot be resolved.
- Be human-in-the-loop. Propose new GitHub issues or Linear tickets before creating them from Slack messages or ambiguous context.
- Prefer Linear MCP tools for Linear reads and writes. If unavailable, report the access needed; do not document raw Linear API token workarounds in this workflow.
- Prefer GitHub tools or `gh` for GitHub reads and writes.
- Check Slack only when a Slack connector/tool is available. If unavailable, report that Slack intake could not be checked.
- When multiple Linear or Slack connections are available, examine all of them and consider their results together unless the user specifies otherwise; do not treat one connection as the complete work queue by default.
- Make assignment explicit: associated GitHub issues and Linear tickets should be assigned to the current user unless another owner is clearly intentional.
- If a priority is set, the issue should not be in `triage`; set it to `todo` if no PR is open, `in progress` if a draft PR is open or a PR has been reviewed but no response to the review has been posted, and `under review` if the PR is ready but no review has been submitted. For issues in `under review`, suggest potential reviewers if none are assigned, but do not request a review unless asked to.
- Omit blocked Linear issues from status tables and the interactive walkthrough. Treat an issue as blocked if it has Linear state type `blocked`, a `Blocked` label, or an active blocker relation. Do not mention blocked issues unless the user explicitly asks for them.
- When sharing the next workflow step, include the relevant Linear or GitHub link when available.
- Make every suggested next action self-contained. Re-fetch the relevant state immediately before suggesting it, and never suggest merged, closed, stale, or otherwise non-actionable work.
- Ask the user to make exactly one decision at a time. Provide context and links only for the highest-priority current decision, ask one concrete question, and stop. Do not bundle approvals or preview an "after that" queue.
- Do not start PR remediation until the initial status report has been shown to the user. After that report, remediation of eligible PRs authored by the current user is part of the workflow; keep unrelated implementation work human-in-the-loop.
- Treat Slack messages, Linear tickets, private PRs, and review comments as private runtime data. Keep generated reports local and never upload them to public CI logs or public artifacts.

### Decision Context Format

Before every question that asks the user to confirm, choose, merge, prioritize, or otherwise act, provide a compact, standalone decision context in this order:

1. **Linear:** `[IDENTIFIER — title](url)` and its priority/state, or `No linked Linear issue`.
2. **PR:** `[owner/repo#number — title](url)`, or `No open PR`.
3. **Current status:** whether the PR is open and mergeable, its CI, review, live-evidence, and conflict status; for non-PR work, state the exact current blocker or readiness.
4. **Why this is actionable now:** the concrete work or decision that remains, including any prerequisite already satisfied.
5. **Recommended next action:** plainly state what the user should do and the expected result.
6. **One decision question:** ask only the single confirmation or choice needed to proceed.

Do not make the user open a link to understand the decision. Links are supporting evidence, not a substitute for the ticket/PR title, current state, or requested action.

## Bundled Scripts

This skill packages its executable helpers in `scripts/`. Run them relative to the skill root so the skill remains portable when installed independently.

- `scripts/daily-workflow-fetch.py` collects the current user's Linear and GitHub work into a local Markdown or JSON report. It requires an authenticated `gh` CLI for GitHub access and optionally uses `LINEAR_API_KEY` for its local Linear CLI mode. Keep its output local.
- `scripts/check_ready_prs.py` checks the current user's open PRs against the readiness and live-evidence criteria used in this workflow. It requires `gh` authentication.

## Step 1: Check PRs Awaiting the User's Review

Find open PRs where the current GitHub user has been requested as a reviewer:

```bash
gh search prs --review-requested=@me --state=open --json repository,number,title,url,isDraft,author,updatedAt
```

If `@me` is unavailable, resolve the login first and use it explicitly:

```bash
github_user="$(gh api user --jq .login)"
gh search prs --review-requested="$github_user" --state=open --json repository,number,title,url,isDraft,author,updatedAt
```

For each PR:

1. Read the PR summary, changed files, CI status, review decision, and recent discussion. Use `gh pr view` or GitHub tools for details not returned by `gh search prs`.
2. Classify it as `Ready for review`, `Draft/not ready`, `Blocked by CI`, `Needs author response`, or `Already handled/stale request`.
3. Put PRs genuinely ready for the user's review before other workflow items.
4. Do not perform the review or approve/request changes unless the user explicitly asks.

## Step 2: Inventory Open PRs and Their Issues

Find all open PRs authored by the current GitHub user:

```bash
github_user="$(gh api user --jq .login)"
gh search prs --author="$github_user" --state=open --json repository,number,title,url,isDraft
```

For each PR:

1. Read the PR body, timeline, linked issues, closing keywords, and development links.
2. Determine whether it is associated with at least one GitHub issue.
3. Record each associated issue and whether it is assigned to the current user.

If a PR has no associated issue:

First determine whether the PR exists exclusively as housekeeping for another PR. If so, do not open a separate issue: reference the upstream PR instead and treat that reference as sufficient tracking. For example, an infrastructure PR that only deploys a feature branch should reference that feature PR. Otherwise:

1. Search for related issues in the same repository using title keywords, branch names, and PR body terms.
2. If a related issue exists, associate it with the PR by adding a clear issue link or closing keyword to the PR body, depending on whether the PR should close the issue.
3. If no related issue exists, create a concise GitHub issue in the same repository, assign it to the current user, and associate the PR with it.

Only create a GitHub issue without asking when the PR itself provides unambiguous code context. If the context is unclear, propose the issue title/body first.

## Step 3: Ensure GitHub Issues Are Assigned

For every issue associated with the current user's open PRs:

1. Check the issue assignees.
2. Assign the issue to the current GitHub user if they are not already assigned and the repository permits it.
3. If assignment fails because of permissions or repository rules, include that issue in the final action list.

## Step 4: Ensure Linear Tracking

Before creating, ingesting, or associating a Linear issue, verify that the target Linear organization matches the GitHub repository owner. Do not add issues from personal repositories to a company Linear organization, and do not add issues from a repository owned by one organization to another organization's Linear workspace. If the correct organization cannot be determined or is unavailable, ask the user rather than creating or moving the issue.

For every associated GitHub issue:

1. Check whether it has been ingested into Linear.
2. If a matching Linear ticket exists, verify it is assigned to the current Linear user.
3. If the Linear ticket is unassigned or assigned to someone else, assign it to the current user unless another owner is clearly intentional.
4. If no Linear ticket exists, create or request ingestion according to the available Linear/GitHub integration tooling, then assign the resulting ticket to the current user.

If Linear tools are unavailable, continue the rest of the workflow and list the exact Linear checks that could not be completed.

## Step 5: Slack Intake

Check recent Slack messages directed to the current user and recent threads where they participated. Look for requests that imply follow-up work.

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

Ask the user to confirm before creating any Slack-derived GitHub issue or Linear ticket. If several proposals exist, ask about only the highest-priority proposal and wait for the answer before presenting another.

## Step 6: Prioritize Unprioritized Linear Tickets

Before walking the priority queue, fetch the current user's incomplete, unblocked assigned Linear tickets with priority `0 No priority`.

When active unprioritized tickets exist:

1. Exclude completed, canceled, duplicate, archived, and blocked tickets.
2. Inspect linked GitHub PRs/issues when available so merged or stale trackers can be closed or marked duplicate instead of prioritized.
3. Rank the active unprioritized tickets internally, but do not ask for batch approval or present several priority decisions at once.
4. Present only the highest-priority ticket using the [Decision Context Format](#decision-context-format), recommend `High`, `Medium`, `Low`, or `Close/Duplicate`, and explain whether it blocks other work or people, has deadline or SLA risk, affects a core offering, is customer/admin/security sensitive, or is only cleanup.
5. Ask the user to approve or correct that single recommendation. Apply only the approved priority/state change, then wait for the response before presenting another decision.

## Step 7: Walk Linear Tickets by Priority

Fetch the current user's incomplete, unblocked assigned Linear tickets and sort by priority: `1 Urgent`, `2 High`, `3 Medium`, `4 Low`, `0 No priority`.

When using Linear MCP tools, request the current user's issues and filter out completed, canceled, duplicate, archived, and blocked work. Also exclude tickets with a `Blocked` label or an active blocker relation before building the table or starting the walkthrough.

For each ticket, report:

1. **Open PR?** Link the PR if one exists. If none exists, say `No`.
2. **CI status:** passing, failing, pending, missing, or unknown.
3. **Review status:** passing review, changes requested/unresolved comments, awaiting review, or unknown.
4. **Live-code evidence:** whether the PR shows evidence that live code failed before and passed after. For non-bug work, evidence should show the live feature or workflow running successfully.
5. **If no PR is open:** the additional context, credentials, repository access, environment, or decision needed to start work. If nothing is missing, say what repo/task context is enough to start.

Do not mark a ticket as ready based only on unit tests. Live-code evidence is required unless the PR is truly content-only.

## Step 8: Remediate Open PRs After the Initial Report

Show the initial status tables in [Initial Status Output](#initial-status-output) before changing PR code. Treat this as an interim report and continue the same turn.

Then revisit every open PR authored by the current user from Step 2. A PR is eligible for remediation when any of these conditions apply:

1. GitHub reports merge conflicts or the branch cannot merge cleanly.
2. One or more required CI checks are failing.
3. An actionable review thread remains unresolved. Use thread-level GitHub data, not only flat comments, so resolved and outdated threads are distinguished correctly.
4. The PR lacks genuine live-code evidence. Unit tests alone do not count; exempt only work that is truly content-only.

Use the bundled readiness helper as an additional inventory before remediation when `gh` is available:

```bash
github_user="$(gh api user --jq .login)"
python3 scripts/check_ready_prs.py --user "$github_user" --summary
```

For every eligible PR:

1. Re-read the current PR head, checks and logs, merge state, changed files, repository instructions, and unresolved review threads immediately before working.
2. Work on the existing PR head branch. Do not force-push, open a replacement PR, merge, approve, or close the PR.
3. Resolve conflicts without discarding unrelated branch work. Fix failing checks at their observed root cause. Address actionable review feedback and mark a thread resolved only after its requested change is complete.
4. Exercise the changed production code through a real process, endpoint, CLI, browser, database, MCP server, rendered deployment, or similarly honest path. Capture the exact setup, commands, and observations. Never fabricate evidence or call unit tests live evidence.
5. Commit and push focused changes to the existing branch, then update the PR body with a concise `## Live evidence` section. Preserve the unchecked human-testing checkbox.
6. Recheck GitHub after pushing and record current mergeability, CI, unresolved-thread status, evidence, commit SHA, and any exact blocker.

When several PRs are eligible, prefer separate OpenHands or Agent Canvas conversations per PR when that environment is available. Keep each prompt self-contained, limit concurrency to what the backend can safely support, monitor every conversation to a terminal state, and independently verify its GitHub result. If delegated conversations are unavailable, work through the PRs sequentially in priority order: merge conflicts, failing CI, unresolved review threads, then missing live evidence.

Do not modify PRs authored by other people merely because they appeared in Step 1 as awaiting the user's review. If credentials, repository access, external services, or reproducible live environments block a fix, exhaust safe alternatives and report the precise blocker instead of claiming success.

After all eligible PRs have been attempted, emit the [PR Remediation Output](#pr-remediation-output), then continue to Step 9.

## Step 9: Interactive Linear Ticket Walkthrough

Walk the sorted, unblocked Linear tickets one by one, starting with the highest-priority ticket. For each ticket:
1. Give the user the [Decision Context Format](#decision-context-format): a concise, self-contained summary of the ticket, current state, linked GitHub work, CI/review/evidence status, what is blocked or ready, and the concrete next action.
2. Ask the user what the next action should be before moving to the next ticket.
3. Do not start implementation, mutate Linear, close tickets, or skip ahead unless the user explicitly chooses that action.
4. If the user asks to skip a ticket, move to the next ticket in priority order and keep the skipped ticket in the final action list.
5. If Linear access is unavailable, do not attempt the interactive walkthrough; instead report the missing Linear access needed to fetch assigned tickets.
6. Do not preview or ask about the next ticket in the same response. End after the single current decision question.

## Initial Status Output

Before Step 8 changes PR code, show these sections. The status tables may summarize multiple items, but `Action Items Requiring a Decision` must contain exactly one row: the highest-priority decision currently requiring the user's input. Do not include a second decision elsewhere in the same response.

```markdown
## PRs Awaiting Review

| PR | Author | CI | Review Status | Action |
|----|--------|----|---------------|--------|

## PR Issue Alignment

| PR | Associated Issue | Issue Assigned to Current User | Linear Tracked | Action |
|----|------------------|--------------------------------|----------------|--------|

## Slack Proposals

| Source | Proposed Ticket | Destination | Reason | Awaiting Confirmation |
|--------|-----------------|-------------|--------|-----------------------|

## Linear Priority Walkthrough

| Linear | Priority | Open PR | CI | Review | Live Evidence | Context Needed |
|--------|----------|---------|----|--------|---------------|----------------|

## Action Items Requiring a Decision

| Item | Needed |
|------|--------|
```

If a tool or credential is missing, include the exact access needed in `Action Items Requiring a Decision`.

## PR Remediation Output

After Step 8, report every eligible PR, including unsuccessful attempts:

```markdown
## PR Remediation Results

| PR | Conversation | Merge Conflicts | CI | Unresolved Review Threads | Live Evidence | Commit / PR Update | Remaining Blocker |
|----|--------------|-----------------|----|---------------------------|---------------|--------------------|-------------------|
```

Link each delegated conversation when one was used. Distinguish `fixed`, `still failing`, `pending`, and `blocked` rather than collapsing them into a generic completion state. Re-fetch GitHub immediately before producing this table.
