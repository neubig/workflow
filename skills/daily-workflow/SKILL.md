---
name: daily-workflow
description: Human-in-the-loop daily workflow ("daily workflow", "my workflow", or "work queue") for checking review requests, aligning GitHub PRs and issues with Linear tickets, and triaging recent Slack requests before remediating the current user's eligible PRs.
---

# Daily Workflow

Use this skill when the user asks to review or organize their daily workflow. First produce a concise report containing all immediate GitHub actions and every actionable Linear issue tied at the highest current priority. Then resolve issue and PR tracking problems. Walk through issues one by one only after that resolution phase finishes or the user explicitly requests the walkthrough.

## Operating Rules

- Resolve the current user before taking action. Use `gh api user --jq .login` for GitHub, the current-user identity from Linear, and the current Slack profile when those services are available. Ask the user when an identity cannot be resolved.
- Be human-in-the-loop. Propose new GitHub issues or Linear tickets before creating them from Slack messages or ambiguous context.
- Use Linear integrations/MCP tools as the authoritative Linear source. Before declaring Linear unavailable, resolve the current user and fetch assigned issues through every exposed Linear connection (including integrations-hub connections). The bundled report helper and its runtime `LINEAR_API_KEYS` value are only an optional local snapshot path; a missing or failed `LINEAR_API_KEYS` check must never be treated as evidence that Linear integrations are unavailable. If an integration read fails, report that specific connection and continue with the others.
- Prefer GitHub tools or `gh` for GitHub reads and writes.
- Check Slack only when a Slack connector/tool is available. If unavailable, report that Slack intake could not be checked.
- Every Linear reference shown to the user must include the human-readable identifier and the exact issue title together, preferably as `[IDENTIFIER — title](url)`. Never output a bare Linear identifier, bare Linear URL, or an identifier without its title in a table, action list, decision context, or summary. If a title is missing or truncated, fetch the issue before reporting it; if it cannot be fetched, report the access problem instead of emitting the bare ID.
- When multiple Linear or Slack connections are available, examine all of them and consider their results together unless the user specifies otherwise; do not treat one connection as the complete work queue by default.
- Make assignment explicit: associated GitHub issues and Linear tickets should be assigned to the current user unless another owner is clearly intentional.
- Maintain exactly one canonical GitHub issue and one canonical Linear ticket for each unit of work. Before any issue creation or Linear ingestion, search every applicable GitHub repository and configured Linear connection using the PR URL/number, linked issue URL, branch name, normalized title, and substantive keywords. Reuse and update an existing tracker even when its title differs. Never launch competing create/ingest operations for the same candidate in parallel. When duplicates already exist, preserve the fuller tracker most directly linked by the PR, mark the others duplicate, and close their redundant GitHub issues with links to the canonical records.
- If a priority is set, the issue should not be in `triage`; set it to `todo` if no PR is open, `in progress` if a draft PR is open or a PR has been reviewed but no response to the review has been posted, and `under review` if the PR is ready but no review has been submitted. For issues in `under review`, suggest potential reviewers if none are assigned, but do not request a review unless asked to.
- Order work by priority first, then by due date within the same priority: overdue dates first, then the earliest upcoming date, then work without a due date. Re-fetch due dates before every recommendation.
- Defer Linear tickets scheduled for a **future cycle** (a team cycle that starts after today) unless every issue in that team's current cycle is complete. `scripts/daily-workflow-fetch.py` applies this automatically: it keeps current/past-cycle tickets and any ticket not assigned to a cycle, and surfaces future-cycle work only once the current cycle has no incomplete issues left.
- Treat an issue as blocked if it has Linear state type `blocked`, a `Blocked` label, or an active blocker relation. Do not present the blocked issue itself as actionable. Before omitting it, inspect its active blocker relations and follow the blocker chain until reaching an actionable issue. If that issue belongs to the current user, surface it as the next action and explain which higher-ranked ticket and deadline it unlocks. If every active blocker belongs to someone else or requires an external event, record the exact dependency internally and continue to the next actionable item.
- When sharing the next workflow step, include the relevant Linear or GitHub link when available.
- Make every suggested next action self-contained. Treat the freshly generated report snapshot as the current state for the initial report. Re-fetch the relevant item after the user selects it and immediately before any mutation; never act on merged, closed, stale, or otherwise non-actionable work.
- During an interactive decision or walkthrough phase, ask the user to make exactly one decision at a time. The main report is not that phase: include every item tied at the highest active priority and do not reduce it to one arbitrary item. Once interaction begins, provide context and links only for the current decision, ask one concrete question, and stop.
- Do not start PR remediation until the initial status report has been shown to the user. After that report, remediation of eligible PRs authored by the current user is part of the workflow; keep unrelated implementation work human-in-the-loop.
- When the current item requests cycle or sprint planning, invoke `$cycle-planning`. Treat labels, dates, roadmap entries, and audits as planning inputs, not approved commitments; do not autonomously finalize the plan or close its planning ticket.
- Treat Slack messages, Linear tickets, private PRs, and review comments as private runtime data. Keep generated reports local and never upload them to public CI logs or public artifacts.

## Workflow Phases

Keep these phases distinct:

1. **Main report:** gather read-only context and report all actionable review/PR items plus every actionable Linear issue tied at the highest active priority. For Linear, `1 Urgent` outranks `2 High`, `3 Medium`, `4 Low`, and `0 No priority`; include every tie at the winning level. Do not cap the report by item count and do not begin the one-by-one walkthrough.
2. **Issue resolution:** after showing the main report, resolve eligible prioritization, Slack intake, issue/PR alignment, assignment, tracking, and remediation work described below. Keep human-in-the-loop requirements intact.
3. **Issue walkthrough:** begin only after the issue-resolution phase is complete or when the user explicitly asks to start it. Present one issue per response with the links and context in [Decision Context Format](#decision-context-format).

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

- `scripts/gather_github_evidence.py` pipelines the review-requested and authored-PR queues into a shared JSON or Markdown snapshot. Its default `report` profile overlaps discovery and low-cost detail reads; use `--profile full` only for remediation detail. Treat its evidence classification and remediation reasons as heuristics, follow every truncation warning with a targeted read, and keep generated reports local.
- `scripts/daily-workflow-fetch.py` generates the action-oriented Markdown or JSON report from the shared GitHub snapshot and optional local Linear data. When `LINEAR_API_KEYS` is available, it fetches every comma-separated Linear connection and GitHub concurrently, then combines their assigned tickets. Keep its output local.
- `scripts/check_ready_prs.py` checks the current user's open PRs against the readiness and live-evidence criteria used in this workflow. It requires `gh` authentication.

## Fast Report Path

Start the initial report with the unified generator. It automatically uses every runtime-provided Linear credential when available and otherwise continues with GitHub only:

```bash
python3 scripts/daily-workflow-fetch.py --output json
```

At the same time, start one batched assigned-ticket read for every additional configured Linear connection and one recent-request search for every configured Slack connection. Do not wait for one source before starting another. Reuse those result sets throughout the initial report instead of repeating identity, list, or per-item reads.

Build and emit the main report from those shared snapshots. Include every tied item at the highest active Linear priority; never apply an arbitrary count limit. Do not run `check_ready_prs.py`, the collector's `full` profile, fetch check names or comment bodies, follow blocker chains beyond a candidate action item, or make per-PR detail reads first. If a source is slower or unavailable, report that source's status without rerunning the completed sources. During the following issue-resolution phase, fetch only the target item's full context and immediately re-fetch it before any mutation.

Use only the read-only portions of Steps 1–7 before emitting the main report. Defer their confirmation questions and mutations until the issue-resolution phase.

Use `daily-workflow-fetch.py --output markdown` for a standalone local report. Use `gather_github_evidence.py --profile full` only after a specific PR needs check names, review-comment bodies, or recent discussion for remediation. Re-fetch the selected target immediately before changing it.

## Step 1: Check PRs Awaiting the User's Review

Use `prs_awaiting_review` from the batched GitHub snapshot. If the collector is unavailable, find open PRs where the current GitHub user has been requested as a reviewer:

```bash
gh search prs --review-requested=@me --state=open --json repository,number,title,url,isDraft,author,updatedAt
```

If `@me` is unavailable, resolve the login first and use it explicitly:

```bash
github_user="$(gh api user --jq .login)"
gh search prs --review-requested="$github_user" --state=open --json repository,number,title,url,isDraft,author,updatedAt
```

For each PR:

1. Read the PR summary, changed files, CI status, review decision, recent discussion, and unresolved thread state. Use the snapshot first; use `gh pr view` or GitHub tools for truncated or missing details.
2. Classify it as `Ready for review`, `Draft/not ready`, `Blocked by CI`, `Needs author response`, or `Already handled/stale request`.
3. Put PRs genuinely ready for the user's review before other workflow items.
4. Do not perform the review or approve/request changes unless the user explicitly asks.

## Step 2: Inventory Open PRs and Their Issues

Use `authored_open_prs` from the batched GitHub snapshot. If the collector is unavailable, find all open PRs authored by the current GitHub user:

```bash
github_user="$(gh api user --jq .login)"
gh search prs --author="$github_user" --state=open --json repository,number,title,url,isDraft
```

For each PR:

1. Read the PR body, timeline, linked issues, closing keywords, and development links. Use the snapshot for the initial inventory and make targeted reads when evidence is missing or truncated.
2. Determine whether it is associated with at least one GitHub issue.
3. Record each associated issue and whether it is assigned to the current user.

If a PR has no associated issue:

First determine whether the PR exists exclusively as housekeeping for another PR. If so, do not open a separate issue: reference the upstream PR instead and treat that reference as sufficient tracking. For example, an infrastructure PR that only deploys a feature branch should reference that feature PR. Otherwise:

1. Search for related issues in the same repository using the PR URL/number, title keywords, branch names, and PR body terms. Treat any issue already linked or closed by the PR as canonical unless it is clearly stale or broader work intentionally needs separate tracking.
2. If a related issue exists, associate it with the PR by adding a clear issue link or closing keyword to the PR body, depending on whether the PR should close the issue.
3. If no related issue exists, create a concise GitHub issue in the same repository, assign it to the current user, and associate the PR with it.

Only create a GitHub issue without asking when the PR itself provides unambiguous code context and the duplicate search returned no candidate. If the context is unclear or a possible match exists, propose the issue title/body or canonical-match decision first.

## Step 3: Ensure GitHub Issues Are Assigned

For every issue associated with the current user's open PRs:

1. Check the issue assignees.
2. Assign the issue to the current GitHub user if they are not already assigned and the repository permits it.
3. If assignment fails because of permissions or repository rules, include that issue in the final action list.

## Step 4: Ensure Linear Tracking

Before creating, ingesting, or associating a Linear issue, verify that the target Linear organization matches the GitHub repository owner. Do not add issues from personal repositories to a company Linear organization, and do not add issues from a repository owned by one organization to another organization's Linear workspace. If the correct organization cannot be determined or is unavailable, ask the user rather than creating or moving the issue.

For every associated GitHub issue:

1. Build a canonical fingerprint from the GitHub issue URL, repository and PR number, PR URL, branch, normalized title, and substantive scope.
2. Search every applicable Linear connection for exact URL matches first and semantic matches second. Also inspect the PR's existing Linear links and attachments.
3. If one matching Linear ticket exists, reuse it and verify it is assigned to the current Linear user.
4. If several matching tickets exist, select the fuller ticket most directly linked by the PR, propose or apply the approved duplicate relations, and ingest nothing new.
5. If the canonical ticket is unassigned or assigned to someone else, assign it to the current user unless another owner is clearly intentional.
6. Only when the full duplicate check returns no match, create or request ingestion, assign the result, then re-query before processing another tracker for the same PR.

If Linear tools are unavailable, continue the rest of the workflow and list the exact Linear checks that could not be completed.

## Step 5: Slack Intake

Check recent Slack messages directed to the current user and recent threads where they participated. Look for requests that imply follow-up work.

Before proposing a Slack-derived ticket, search the applicable GitHub and Linear connections for the same request, links, PR, customer, and substantive scope. Classify an already-tracked request as `No ticket` and link the canonical record instead of proposing another tracker.

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

For the main report, record the applicable unprioritized cohort without asking a question. Defer the recommendation and confirmation loop below until the issue-resolution phase.

When active unprioritized tickets exist:

1. Exclude completed, canceled, duplicate, and archived tickets. Inspect blocked candidates and their active blocker chains before removing them from the actionable queue.
2. Inspect linked GitHub PRs/issues when available so merged or stale trackers can be closed or marked duplicate instead of prioritized.
3. Rank the active unprioritized tickets internally. When two tickets receive the same recommended priority, put the earlier due date first; put undated work after dated work. If the leading ticket is blocked, surface its highest-ranked actionable blocker instead.
4. Present only the highest-priority ticket using the [Decision Context Format](#decision-context-format), recommend `High`, `Medium`, `Low`, or `Close/Duplicate`, and explain whether it blocks other work or people, has deadline or SLA risk, affects a core offering, is customer/admin/security sensitive, or is only cleanup.
5. Ask the user to approve or correct that single recommendation. Apply only the approved priority/state change, then wait for the response before presenting another decision.

## Step 7: Build the Highest-Priority Linear Report Cohort

Fetch the current user's incomplete assigned Linear tickets. Sort first by priority: `1 Urgent`, `2 High`, `3 Medium`, `4 Low`, `0 No priority`. Select every actionable ticket tied at the first priority level that contains actionable work. Within that cohort, sort overdue tickets first, then by ascending due date, then place tickets without a due date last. Keep lower-priority tickets out of the main report; they remain available for the later walkthrough.

For every Linear source, request the current user's issues and filter out completed, canceled, duplicate, and archived work. Inspect blocked states, `Blocked` labels, and active blocker relations before building the actionable queue. Replace a blocked candidate with its highest-ranked active blocker when that blocker is actionable by the current user; follow nested blocker relations recursively. Do not let a later deadline at the same priority jump ahead merely because the earlier ticket is blocked.

For each ticket in the selected cohort, report:

1. **Linear:** always render `[IDENTIFIER — exact title](url)`; this field is mandatory even when the ticket has no PR.
2. **Open PR?** Link the PR if one exists. If none exists, say `No`.
3. **CI status:** passing, failing, pending, missing, or unknown.
4. **Review status:** passing review, changes requested/unresolved comments, awaiting review, or unknown.
5. **Live-code evidence:** whether the PR shows evidence that live code failed before and passed after. For non-bug work, evidence should show the live feature or workflow running successfully.
6. **If no PR is open:** the additional context, credentials, repository access, environment, or decision needed to start work. If nothing is missing, say what repo/task context is enough to start.

Before emitting any report, scan every Linear table row and action item for a bare identifier or URL. Replace it with the identifier, exact title, and link, or stop and fetch the missing title.

Do not mark a ticket as ready based only on unit tests. Live-code evidence is required unless the PR is truly content-only.

## Step 8: Remediate Open PRs After the Initial Report

Show the main status tables in [Initial Status Output](#initial-status-output) before changing PR code. This work belongs to the issue-resolution phase; it does not start the one-by-one issue walkthrough.

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

Use `remediation_candidate_reasons` from the batched snapshot to build the initial candidate list, then apply the eligibility rules above and re-fetch each candidate before working.

For every eligible PR:

1. Re-read the current PR head, checks and logs, merge state, changed files, repository instructions, and unresolved review threads immediately before working.
2. Work on the existing PR head branch. Do not force-push, open a replacement PR, merge, approve, or close the PR.
3. Resolve conflicts without discarding unrelated branch work. Fix failing checks at their observed root cause. Address actionable review feedback and mark a thread resolved only after its requested change is complete.
4. Exercise the changed production code through a real process, endpoint, CLI, browser, database, MCP server, rendered deployment, or similarly honest path. Capture the exact setup, commands, and observations. Never fabricate evidence or call unit tests live evidence.
5. Commit and push focused changes to the existing branch, then update the PR body with a concise `## Live evidence` section. Preserve the unchecked human-testing checkbox.
6. Recheck GitHub after pushing and record current mergeability, CI, unresolved-thread status, evidence, commit SHA, and any exact blocker.

When several PRs are eligible, prefer separate OpenHands or Agent Canvas conversations per PR when that environment is available. Keep each prompt self-contained, limit concurrency to what the backend can safely support, monitor every conversation to a terminal state, and independently verify its GitHub result. If delegated conversations are unavailable, work through the PRs sequentially in priority order: merge conflicts, failing CI, unresolved review threads, then missing live evidence.

Do not modify PRs authored by other people merely because they appeared in Step 1 as awaiting the user's review. If credentials, repository access, external services, or reproducible live environments block a fix, exhaust safe alternatives and report the precise blocker instead of claiming success.

After all eligible PRs have been attempted, emit the [PR Remediation Output](#pr-remediation-output). Continue to Step 9 only when the issue-resolution phase is complete; the user may also request Step 9 earlier.

## Step 9: Interactive Linear Ticket Walkthrough

Enter this phase only after issue resolution is complete or when the user explicitly requests it. Re-fetch the sorted, actionable Linear tickets, then walk them one by one, starting with the highest priority and earliest due date. For each ticket:
1. Give the user the [Decision Context Format](#decision-context-format): a concise, self-contained summary of the ticket, current state, linked GitHub work, CI/review/evidence status, what is blocked or ready, and the concrete next action.
2. If the ticket is blocked, follow its active blocker chain. Present the first actionable blocker instead and state the blocked ticket's priority and deadline that make the blocker timely.
3. If the ticket requests cycle or sprint planning, switch to `$cycle-planning` and facilitate the planning session. Resume this walkthrough only after the session is completed or the user explicitly defers it.
4. Ask the user what the next action should be before moving to the next ticket.
5. Do not start implementation, mutate Linear, close tickets, or skip ahead unless the user explicitly chooses that action.
6. If the user asks to skip a ticket, move to the next ticket in the same priority by due date, then continue in priority order, and keep the skipped ticket in the final action list.
7. If Linear access is unavailable, do not attempt the interactive walkthrough; instead report the missing Linear access needed to fetch assigned tickets.
8. Do not preview or ask about the next ticket in the same response. End after the single current decision question.

## Initial Status Output

Before Step 8 changes PR code, show these sections. The main report is a complete status report for the highest active priority cohort, not an interactive decision prompt. Include every tied actionable item; do not cap the table or ask the user to choose one yet.

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

## Highest-Priority Linear Items

The `Linear` cell must always contain `[IDENTIFIER — exact title](url)`. Bare identifiers and bare URLs are invalid output.

| Linear | Priority | Open PR | CI | Review | Live Evidence | Context Needed |
|--------|----------|---------|----|--------|---------------|----------------|

## Highest-Priority Action Items

| Item | Priority | Needed |
|------|----------|--------|
```

If a tool or credential is missing, include the exact access needed in `Highest-Priority Action Items`.

## PR Remediation Output

After Step 8, report every eligible PR, including unsuccessful attempts:

```markdown
## PR Remediation Results

| PR | Conversation | Merge Conflicts | CI | Unresolved Review Threads | Live Evidence | Commit / PR Update | Remaining Blocker |
|----|--------------|-----------------|----|---------------------------|---------------|--------------------|-------------------|
```

Link each delegated conversation when one was used. Distinguish `fixed`, `still failing`, `pending`, and `blocked` rather than collapsing them into a generic completion state. Re-fetch GitHub immediately before producing this table.
