---
name: sprint-planning
description: Facilitate collaborative, human-in-the-loop sprint or Linear cycle planning. Use when the user asks to plan a sprint/cycle, choose sprint scope, set a Sprint Goal, review capacity or carryover, sequence release work into a cycle, or work through a planning ticket surfaced by daily-workflow.
---

# Sprint Planning

Facilitate the planning conversation. Gather evidence and make recommendations, but leave goals, scope, ownership, estimates, and commitments to the user and team.

## Operating Rules

- Treat every generated plan as a proposal until the user explicitly approves it.
- Ask for one decision at a time. Do not silently turn a label, due date, roadmap, or issue description into an approved sprint plan.
- Do not create issues or change cycles, states, priorities, estimates, assignees, or due dates until the user approves the exact change.
- If planning starts from a Linear planning ticket, keep it `In Progress` throughout the conversation. Mark it `Done` only after the user confirms the final plan.
- Let the people doing the work assess feasibility, size the work, and accept ownership. Never fill a person's calendar or assign work merely because they appear available.
- Describe selected backlog items as a **forecast**. The team commits to the agreed cycle themes and quality bar, not an immutable list of items.
- Keep release roadmaps separate from sprint scope. A release date is an input; a Linear cycle is a time box, not a release.
- Count existing work in progress and unfinished carryover before adding new work.
- Resolve the required product surface before evaluating a capability. Evidence from a CLI, API, SDK, mock, or different frontend does not prove that the required user experience works.
- Keep private ticket, customer, personnel, and capacity details in authorized tools and local output.

## Planning Flow

### 1. Establish the Planning Frame

Resolve and re-fetch:

- team and participants
- sprint/cycle dates and cadence
- required product surface and deployment environment
- Product Goal, release milestones, deadlines, and non-goals
- current work in progress and likely carryover
- previous three comparable cycles: forecast, completed work, rollover, and interruption rate
- upcoming availability changes, support/on-call load, holidays, and known interruptions
- the team's Definition of Done and one improvement item from the last retrospective

Do not assume missing capacity or stakeholder information. State what is unknown and ask the user for the single most important missing input.

### 2. Agree on Why: Draft the Cycle Themes

Start with value, not a list of tickets. Draft a small, coherent set of outcome-oriented themes. Do not force unrelated OSS outcomes into one Sprint Goal. For each theme capture:

- the user or stakeholder outcome
- why it matters this cycle
- the observable evidence that would show progress or success
- explicit non-goals when they protect focus

Present the themes and ask the user to confirm, combine, split, or revise them before selecting scope.

### 3. Prepare Candidate Work

Use release objectives and labeled issues to find candidate product areas, then inspect how the actual product works on the required surface. Do not merely paraphrase ticket titles or substitute evidence from another interface. Derive clear `I can ...` statements from the abilities a person should have, and verify each statement against documentation, code, or live-product evidence.

Write each statement with enough context to test it: persona when relevant, action, important conditions or constraints, and observable result. Classify it as:

- **Supported:** reproducibly possible now. Scope documentation, examples, discoverability, or evidence rather than unnecessary implementation.
- **Product gap:** not currently possible or reliable. Treat the statement as an implementation target with acceptance criteria.
- **Unknown:** current behavior has not been verified. Add an investigation decision before committing implementation or documentation work.

Order the resulting statements by contribution to the confirmed themes. For each candidate, check:

- a specific, testable `I can ...` outcome and its current-behavior classification
- acceptance criteria and the applicable Definition of Done
- a small enough vertical slice to finish inside the sprint
- estimate or comparable sizing evidence from the people doing the work
- dependencies, blockers, external approvals, and required collaborators
- validation or live-evidence expectations
- whether the likely owner has confirmed availability

Return vague, unverified, oversized, or blocked work to refinement unless resolving the uncertainty or blocker is part of a confirmed theme. Do not create every discovered gap immediately; propose follow-up work one decision at a time.

### 4. Build a Capacity-Based Forecast

Use recent completed work as a forecast, not a quota. Adjust it for:

- team composition and availability changes
- existing work in progress and carryover
- support, meetings, operational work, and expected interruptions
- quality, review, documentation, release, and evidence work required by the Definition of Done
- an explicit buffer based on the team's historical unplanned-work rate

When reliable cycle history is missing, inspect merged work from the previous four completed weeks. Use repository, change type, review/evidence quality, and recurring technical area to infer each person's likely fit. Exclude bots, automated bumps, mechanical backports, and generated changes from the qualitative assessment. Do not translate PR counts or lines changed directly into points or hours.

Set unavailable capacity to zero and time-box partial availability explicitly. Give someone joining mid-cycle work whose prerequisites can be ready when they return; do not place them on an earlier critical-path dependency.

Do not optimize for full utilization. Prefer credible themes with slack for uncertainty over a larger fragile scope.

Separate the proposed backlog into:

1. **Theme-critical forecast:** the minimum coherent set needed to achieve the cycle themes.
2. **Stretch:** ordered work that may be pulled only if capacity appears.
3. **Not selected:** relevant work excluded with a short reason.

Show totals against the capacity forecast, then ask the user to confirm or adjust the proposed scope.

### 5. Build the Release Dependency and Topic Plan

For each release in or immediately after the cycle, work backward from its acceptance date. Include every dependency required to make the release claim true:

1. releasable product behavior on the required surface
2. deployment or packaging needed to exercise it
3. reproducible live evidence for every selected `I can ...` statement
4. documentation, examples, and other release artifacts that depend on that evidence
5. final acceptance and contingency time

Represent dependencies explicitly as predecessor-successor edges with an owner and needed-by date. A release is not covered when one of its dependencies finishes after the release date or lacks a confirmed owner.

Propose a small list of outcome-oriented topic lanes for each available person. For every lane show why it fits the person's recent demonstrated work, its availability window, dependencies, expected result, and release served. Keep ownership provisional until that person or the user confirms it.

### 6. Plan Enough to Start

After scope is approved, facilitate a lightweight delivery plan. For each selected item record:

- confirmed owner or pairing group
- first executable step
- dependency or handoff
- validation and Definition-of-Done check
- material risk and mitigation

Decompose work into items of roughly a day or less when that improves coordination, but do not invent a detailed day-by-day plan. The plan should remain adaptable as the team learns.

### 7. Run the Confidence Check

Before writing changes, summarize:

- cycle themes and dates
- capacity assumptions
- theme-critical forecast and stretch work
- carryover and work-in-progress treatment
- owners and dependencies
- per-person topic lanes and availability windows
- Definition of Done and validation expectations
- retrospective improvement item
- unresolved risks or decisions

Ask whether the team has enough confidence to start. If confidence is low, reduce scope or resolve the highest risk; do not record a low-confidence plan as final.

### 8. Apply the Confirmed Plan

Only after explicit final approval:

1. Update the Linear cycle and selected issues.
2. Apply confirmed owners, estimates, states, and due dates.
3. Create only the follow-up issues the user approved.
4. Record the cycle themes, capacity assumptions, forecast, stretch work, risks, and confidence decision on the planning ticket or agreed planning document.
5. Re-fetch the updated state and show the user exactly what changed.
6. Mark the planning ticket `Done` only if the user explicitly confirms planning is complete.

## Output Format

Use this compact structure during the final confirmation:

```markdown
## Proposed Sprint Plan

**Cycle Themes:** ...
**Dates:** ...
**Capacity:** ...
**Required Product Surface:** ...
**Definition of Done:** ...

| Theme | I can... | Current Behavior | Work Type | Estimate | Owner | Validation |
|---|---|---|---|---:|---|---|

### Topic Lanes

| Person | Availability | Topics | Demonstrated Fit | Dependencies | Release |
|---|---|---|---|---|---|

### Dependency Schedule

| Predecessor | Successor | Owner | Needed By | Evidence |
|---|---|---|---|---|

### Stretch

| Item | Pull Condition |
|---|---|

### Risks and Open Decisions

- ...

### Confidence

...
```

End with one concrete approval or adjustment question.
