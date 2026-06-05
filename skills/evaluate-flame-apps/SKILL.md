---
name: evaluate-flame-apps
description: This skill should be used when the user asks to "evaluate FLAME applications", "review FLAME cluster apps", "score FLAME proposals", "allocate FLAME GPUs", "plan FLAME cluster allocations", or mentions the FLAME high-priority rubric. It evaluates undecided FLAME cluster applications from the shared spreadsheet, scores them with the rubric, plans allocations across 32 nodes, and writes results to a new sheet or CSV without modifying existing sheets.
triggers:
- evaluate FLAME applications
- FLAME cluster apps
- FLAME allocations
- score FLAME proposals
- FLAME high priority rubric
- allocate FLAME GPUs
---

# Evaluate FLAME Cluster Applications

Evaluate FLAME cluster applications that do not already have decisions, score them with the FLAME high-priority rubric, and produce a non-destructive allocation plan for a 32-node cluster. Preserve existing spreadsheet tabs exactly as-is. Write results only to a newly created evaluation sheet when edit access is available, or to a CSV file for upload when access is unavailable.

## Source Data

Primary spreadsheet:

```text
https://docs.google.com/spreadsheets/d/1JykgeTEpCl5uh1LrzqGeQQtFhZWp7Z52vXBH9fp2rKQ/edit?gid=1803896643#gid=1803896643
```

Try a read-only CSV export first:

```text
https://docs.google.com/spreadsheets/d/1JykgeTEpCl5uh1LrzqGeQQtFhZWp7Z52vXBH9fp2rKQ/export?format=csv&gid=1803896643
```

If the spreadsheet returns 401/403, login wall, or incomplete data, stop and ask for an exported CSV/XLSX or authorized sheet access. Do not infer application details from memory.

## Workflow

1. **Load applications.** Import the sheet into a table. Preserve source row numbers. Normalize flexible header names for applicant, project title, proposal text, request details, decision/status, requested GPUs, requested nodes, requested duration, requested node-hours/GPU-hours, and any links or reviewer notes.
2. **Identify undecided rows.** Treat rows with non-empty decision/status/outcome fields as already decided. Evaluate only rows without decisions. Keep decided rows only for capacity/current-allocation context if they include active approved allocations.
3. **Extract current allocation.** Determine active allocations from approved/allocated rows with start/end dates or explicit current-allocation fields. Use a hard cap of 32 simultaneous nodes. If GPU-per-node is not stated, report the assumption used instead of silently inventing one.
4. **Score each undecided application.** Assign three 1-5 rubric scores: potential impact, preliminary evaluation, and compute justification. Cite direct evidence whenever possible with exact quotes from the proposal and source row/field names. Use external links only when they appear in the application or are needed to verify claims.
5. **Recommend a decision.** Choose one of: `Approve`, `Approve reduced`, `Waitlist / needs info`, or `Reject`. Reject or reduce requests that are poorly justified, infeasible under the 32-node cap, or low-priority relative to other applications.
6. **Plan allocations.** Sort primarily by composite score, then by potential impact, then by preliminary evaluation, then by compute-justification score. Allocate high-value, well-justified proposals first. Stagger jobs so total active nodes never exceeds 32 after accounting for current allocations. Reduce over-large requests when evidence supports a smaller allocation. Include start date, end date/duration, approved nodes, approved GPUs, node-hours, GPU-hours, and rationale.
7. **Write results non-destructively.** If Google Sheets edit access exists, create a new tab named `FLAME Evaluations YYYY-MM-DD` or similar. If not, create `flame_app_evaluations_YYYY-MM-DD.csv` locally and tell the user it is ready for upload. Never modify existing tabs.

## FLAME High-Priority Rubric

Score each dimension independently. If no option directly applies, estimate the closest level and explain the approximation.

### Potential Impact

| Score | Meaning |
|---|---|
| 1 | No paper or model release expected. |
| 2 | Enables more extensive parameter sweeps or ablations for an existing paper. |
| 3 | Produces a model beating a comparable baseline, or a minor insight useful within the researcher’s niche. |
| 4 | Produces a model that is SOTA for its model size on well-known tasks, or a broadly applicable insight/dataset interesting to many researchers. |
| 5 | Releases a model achieving SOTA or rivaling top closed models on major tasks, or creates a major insight/dataset likely to be picked up by top research institutions. |

### Preliminary Evaluation

| Score | Meaning |
|---|---|
| 1 | No preliminary work. |
| 2 | Code implemented but not tested at smaller scale. |
| 3 | Some smaller-scale results are presented. |
| 4 | Smaller-scale results are complete, but not yet scaled. |
| 5 | Scaling curves for smaller models or datasets already exist, and more compute is needed to extrapolate the curves. |

### Justification for Compute Requested

| Score | Meaning |
|---|---|
| 1 | No justification provided. |
| 2 | Necessity for compute is justified, but not the amount of compute. |
| 3 | No concrete numbers are provided. |
| 4 | Concrete numbers are provided, but they do not clearly require the requested compute, or the request exceeds what the numbers suggest. |
| 5 | Concrete numbers allow derivation of requested node-hours, and the derived numbers match the request. |

## Scoring and Decision Guidance

Compute a simple composite score as the mean of the three rubric scores unless the user specifies weights. Use the composite to prioritize, not to automate decisions blindly.

Suggested decision thresholds:

| Pattern | Default recommendation |
|---|---|
| Composite >= 4.0 and compute score >= 4 | Approve if capacity fits. |
| Impact >= 4 and preliminary >= 3 but compute score <= 3 | Approve reduced or request clarification. |
| Composite 3.0-3.9 | Approve reduced or waitlist depending on capacity. |
| Impact <= 2 and preliminary <= 2 | Reject unless there is a strategic reason. |
| Compute score = 1 with no derivable need | Reject or waitlist for clarification even if impact is promising. |

Prefer reductions over rejection when the idea is high-impact but compute math is weak. Prefer rejection when the application lacks both preliminary evidence and a concrete output plan.

## Allocation Planning Rules

- Treat 32 nodes as the maximum concurrent allocation, not a total budget, unless the sheet explicitly defines a different total-budget interpretation.
- Include current approved allocations before scheduling new ones.
- Allocate in whole nodes when the cluster scheduler is node-granular. Convert nodes to GPUs using the sheet’s stated GPUs-per-node value. If unknown, include both approved nodes and the assumed/unknown GPU count.
- Use requested deadlines or project dates when available. Otherwise schedule from the current date, highest-priority first.
- Keep a running calendar of active node usage. Do not schedule a new allocation window that causes total active nodes to exceed 32.
- For reduced approvals, explain the reduction in terms of rubric evidence: insufficient compute derivation, partial preliminary validation, or capacity pressure.
- For waitlisted applications, state the missing information needed to reconsider.

## Output Schema

Create columns with these names or close equivalents:

```text
Source Row, Applicant, Project Title, Existing Decision, Impact Score,
Impact Evidence, Preliminary Score, Preliminary Evidence,
Compute Justification Score, Compute Evidence, Composite Score,
Recommendation, Approved Nodes, Approved GPUs, Duration,
Start Date, End Date, Approved Node-Hours, Approved GPU-Hours,
Allocation Rationale, Conditions / Follow-up, Citation Notes
```

Add a metadata note at the top of a new sheet or in the CSV comments when the target format allows comments: `Created by an AI agent (OpenHands) on behalf of the user.` If CSV comments are not practical, include a `Generated By` column or a first metadata row.

Evidence columns should contain short exact quotes, for example: `Row 12, Proposal Summary: "..."`. Avoid unsupported claims. When the application links to external artifacts such as papers, repos, model cards, or prior results, cite those links in `Citation Notes` and use them to support the score only after reading them.

## Google Sheet Upload Procedure

Use Google Sheets API or browser editing only when authenticated access is already available. Create a new tab; do not edit, sort, filter, delete, or overwrite existing tabs. Before writing, prepare the full table locally and verify row counts, source row references, and formulas/values.

If sheet upload is not possible, save a CSV file in the working directory and report its absolute path. Make the CSV directly uploadable to a new Google Sheet tab.
