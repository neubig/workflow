# Daily Workflow

This document describes my daily workflow for managing tasks and code contributions.

## Overview

The workflow consists of three main phases:

1. **Linear Tickets** - Work on highest priority assigned tickets
2. **Ready PRs** - Monitor PRs awaiting review/merge
3. **Draft PRs** - Work on PRs that need development

## Prerequisites

### Required API Access
- **Linear API Key** (`LINEAR_API_KEY`) - For accessing Linear tickets
- **GitHub Token** (`GITHUB_TOKEN`) - For GitHub API and CLI operations

### User Identifiers
- Linear: `graham@openhands.dev` (or associated email)
- GitHub: `neubig`

---

## Phase 1: Linear Tickets

### Fetch Assigned Tickets

Use the Linear GraphQL API to fetch tickets assigned to you:

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_API_KEY" \
  -d '{
    "query": "query { viewer { assignedIssues(first: 50, filter: { state: { type: { nin: [\"completed\", \"canceled\"] } } }) { nodes { identifier title priority priorityLabel state { name type } description createdAt updatedAt } } } }"
  }' | jq '.data.viewer.assignedIssues.nodes'
```

### Priority Levels
| Priority | Label | Action |
|----------|-------|--------|
| 1 | Urgent | Work on immediately |
| 2 | High | Work on first (before medium/low) |
| 3 | Medium | Work on after high priority |
| 4 | Low | Work on when higher priorities are clear |

### Processing Tickets

1. **Sort by priority** - Work on highest priority (lowest number) first
2. **Check status** - Focus on "In Progress" tickets first, then "Todo"
3. **Review description** - Some tickets may only have Slack links (manual action needed)
4. **Categorize** - Some tickets require manual action (e.g., "Contact X", "Send email to Y")

#### Tickets Requiring Manual Action
These should be added to a personal action list rather than automated:
- Tickets with only Slack links as description
- Tickets about contacting people/companies
- Tickets about sending communications
- Tickets requiring discussions/meetings

---

## Phase 2: Ready PRs (Not Draft)

### Fetch Ready PRs

```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/search/issues?q=is:pr+is:open+author:neubig+draft:false" | jq '.items'
```

### Check Review Status

For each ready PR, check if it has unresolved review threads:

```bash
gh api graphql -f query='
{
  repository(owner: "OWNER", name: "REPO") {
    pullRequest(number: PR_NUMBER) {
      reviewThreads(first: 50) {
        nodes {
          id
          isResolved
          comments(first: 3) {
            nodes { body author { login } }
          }
        }
      }
    }
  }
}'
```

### Decision Tree for Ready PRs

```
PR is Ready (not draft)
├── Has unresolved review comments?
│   └── YES → Move back to draft, work on reflecting comments
│   └── NO → Has been ready for 2+ business days?
│       └── YES → Ping reviewer on Slack
│       └── NO → Wait for review
```

### Moving PR to Draft

If review feedback hasn't been reflected:
```bash
gh pr ready --undo PR_NUMBER --repo OWNER/REPO
```

---

## Phase 3: Draft PRs

### Fetch Draft PRs

```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/search/issues?q=is:pr+is:open+author:neubig+draft:true" | jq '.items'
```

### Working on Draft PRs

#### 1. Reflect Review Comments

If the PR has review comments:

1. **Fetch unresolved threads**:
   ```bash
   gh api graphql -f query='
   {
     repository(owner: "OWNER", name: "REPO") {
       pullRequest(number: PR_NUMBER) {
         reviewThreads(first: 50) {
           nodes { id isResolved comments(first: 5) { nodes { body } } }
         }
       }
     }
   }'
   ```

2. **Address each comment**:
   - Implement the suggested changes, OR
   - Explain why the suggestion won't be implemented (if it would add significant complexity with little value)

3. **Reply and resolve threads**:
   ```bash
   # Reply to thread
   gh api graphql -f query='
   mutation {
     addPullRequestReviewThreadReply(input: {
       pullRequestReviewThreadId: "THREAD_ID"
       body: "Fixed in COMMIT_SHA"
     }) { comment { id } }
   }'
   
   # Resolve thread
   gh api graphql -f query='
   mutation {
     resolveReviewThread(input: {threadId: "THREAD_ID"}) {
       thread { isResolved }
     }
   }'
   ```

4. **IMPORTANT: Iterate Until All Reviews Resolved**
   
   After pushing fixes and resolving threads, **always re-check for new reviews**. Bots may add new comments on your new code:
   
   ```bash
   # Check for unresolved reviews
   gh api graphql -f query='
   {
     repository(owner: "OWNER", name: "REPO") {
       pullRequest(number: PR_NUMBER) {
         reviewThreads(first: 30) {
           nodes { isResolved }
         }
       }
     }
   }' | jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length'
   ```
   
   **Repeat the cycle until the count is 0:**
   - If new unresolved reviews appear → Address them
   - Push fixes → Re-check for new reviews
   - Continue until no unresolved reviews remain

#### 2. Demonstrate Functionality (CRITICAL)

**This is NOT just running unit tests** - it requires live demonstration of behavior.

**For Bug Fix PRs:**
1. Clone the repo and checkout the base branch (before the fix)
2. Run the code that triggers the bug - capture the error output
3. Checkout the PR branch (with the fix)
4. Run the same code - demonstrate the bug no longer occurs
5. Include both outputs in PR comments if not already documented

**For New Feature PRs:**
1. Clone the repo and checkout the PR branch
2. Install dependencies and set up environment
3. Run the feature in a live setting with real inputs/outputs
4. Capture and document the successful execution

**PRs That CANNOT Be Live Tested Without Special Resources:**
Keep these as draft until testing is possible:
- Model changes (e.g., adding new LLM model names) - need API keys
- CI/CD configs (e.g., Jenkinsfile) - need CI server access
- Platform-specific fixes (e.g., Windows-only code) - need that platform
- External service integrations - need credentials/access

**Content-Only PRs (no live testing needed):**
- Documentation updates
- Blog posts
- README changes
- Comment/docstring additions

#### 3. Check for Bot Reviews (ITERATIVE PROCESS)

After marking a PR ready, automated bots (e.g., `all-hands-bot`) may add review comments. **This is an iterative process** - bots may review your fixes and add new comments.

**The Complete Bot Review Loop:**

```
┌─────────────────────────────────────────────────────────────┐
│  1. Check for unresolved reviews                            │
│     ↓                                                       │
│  2. If unresolved > 0:                                      │
│     a. Move PR to draft                                     │
│     b. Address each review comment                          │
│     c. Push fixes                                           │
│     d. Resolve review threads                               │
│     e. Mark PR ready                                        │
│     f. GOTO step 1 (bot may review new code!)               │
│     ↓                                                       │
│  3. If unresolved == 0:                                     │
│     ✓ PR is ready for human review                          │
└─────────────────────────────────────────────────────────────┘
```

**Check for unresolved reviews:**
```bash
gh api graphql -f query='
{
  repository(owner: "OWNER", name: "REPO") {
    pullRequest(number: PR_NUMBER) {
      reviewThreads(first: 30) {
        nodes {
          isResolved
          comments(first: 1) {
            nodes { body author { login } }
          }
        }
      }
    }
  }
}'
```

**Move PR back to draft if bot reviews found:**
```bash
gh api graphql -f query='
mutation {
  convertPullRequestToDraft(input: {pullRequestId: "PR_ID"}) {
    pullRequest { isDraft }
  }
}'
```

**Mark PR ready after addressing all reviews:**
```bash
gh api graphql -f query='
mutation {
  markPullRequestReadyForReview(input: {pullRequestId: "PR_ID"}) {
    pullRequest { isDraft }
  }
}'
```

**Best Practice: Batch Check All Ready PRs**

Run this periodically to check all ready PRs for new bot reviews:
```bash
for pr_info in "Owner/Repo/PR_NUM" "Owner2/Repo2/PR_NUM2"; do
  owner=$(echo $pr_info | cut -d'/' -f1)
  repo=$(echo $pr_info | cut -d'/' -f2)
  num=$(echo $pr_info | cut -d'/' -f3)
  unresolved=$(gh api graphql -f query="{ repository(owner: \"$owner\", name: \"$repo\") { pullRequest(number: $num) { reviewThreads(first: 30) { nodes { isResolved } } } } }" | jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length')
  if [ "$unresolved" != "0" ]; then
    echo "⚠️  $owner/$repo#$num: $unresolved unresolved"
  else
    echo "✅ $owner/$repo#$num: OK"
  fi
done
```

---

## Parallel Processing

When multiple independent tasks exist, they can be worked on in parallel:

### Options for Parallelization
1. **OpenHands Cloud API** - Delegate tasks to separate agent instances
2. **Delegate Tool** - Use built-in delegation capabilities
3. **Manual Batching** - Group API calls that don't depend on each other

### Example: Parallel API Calls
```bash
# Fetch Linear tickets and GitHub PRs simultaneously
curl -s ... (Linear API) &
curl -s ... (GitHub API) &
wait
```

---

## Quick Reference

### Daily Checklist

- [ ] Fetch Linear tickets assigned to me
- [ ] Identify high-priority tickets requiring attention
- [ ] List tickets requiring manual action (Slack pings, emails)
- [ ] Check ready PRs for review status
- [ ] **Check ready PRs for NEW bot reviews (iterative!)**
- [ ] Move PRs with unresolved reviews back to draft
- [ ] Identify PRs needing reviewer pings (>2 business days)
- [ ] Check draft PRs for unresolved review comments
- [ ] Work on draft PRs to address feedback or demonstrate functionality
- [ ] After marking PRs ready, **re-check for bot reviews** (repeat until 0)

### Key Commands

| Action | Command |
|--------|---------|
| List failed CI runs | `gh run list --status failure --limit 5` |
| View CI failure logs | `gh run view RUN_ID --log-failed` |
| Move PR to draft | `gh pr ready --undo PR_NUMBER` |
| Mark PR as ready | `gh pr ready PR_NUMBER` |
| List PR review threads | Use GraphQL query above |
| Resolve review thread | Use GraphQL mutation above |

---

## Notes

- **Business days**: Weekdays (Monday-Friday), excluding holidays
- **Slack links in Linear**: These require manual review and action
- **Review comment policy**: Not all feedback needs to be implemented - use judgment on value vs. complexity

---

## PR Status Tracking Template

Use this template to track PR status during workflow:

| PR | Repo | Status | Blockers | Action Needed |
|----|------|--------|----------|---------------|
| #XX | org/repo | draft/ready | none/review/testing | description |

### Status Meanings:
- **draft** - Needs work before review
- **ready** - Ready for reviewer attention
- **blocked** - Cannot proceed (missing resources/access)
- **pending-merge** - Approved, waiting for merge

### Common Blockers:
- `bot-review` - Automated review found issues
- `human-review` - Waiting for human reviewer
- `testing` - Cannot live test without resources
- `ci-failure` - CI checks failing
- `merge-conflict` - Needs rebase/merge from main
