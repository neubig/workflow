---
name: github-pr-workflow
description: Complete GitHub PR workflow including live testing requirements and iterative review resolution. Use when managing PRs from creation through merge.
triggers:
- pr review
- bot review
- review iteration
- unresolved reviews
- live test
- demonstrate pr
---

# GitHub PR Workflow

This skill covers the complete PR workflow: live testing to demonstrate functionality, and iterative review resolution until all comments are addressed.

## Part 1: Live Testing Requirements

<IMPORTANT>
Unit tests are NOT sufficient. PRs must demonstrate actual behavior in a live setting before being marked ready for review.
</IMPORTANT>

### Bug Fix PRs

Demonstrate both states and **add evidence to PR description**:

1. **Before the fix** - Show the bug exists on the base branch:
   ```bash
   git checkout main
   # Run code that triggers the bug
   # Capture error output
   ```

2. **After the fix** - Show the bug is resolved:
   ```bash
   git checkout pr-branch
   # Run same code
   # Show bug no longer occurs
   ```

3. **Add to PR description**:
   ```markdown
   ## Evidence
   
   **Before (on main):**
   ```
   $ python script.py
   Error: Something broke
   ```
   
   **After (this PR):**
   ```
   $ python script.py
   Success!
   ```
   ```

### New Feature PRs

1. Set up environment with PR changes
2. Run the feature with real inputs
3. Capture and document successful execution
4. **Add evidence to PR description**:
   ```markdown
   ## Evidence
   
   **Feature working:**
   ```
   $ my-new-command --flag
   ✓ Feature executed successfully
   Output: expected result
   ```
   ```

### PRs That Cannot Be Live Tested

<IMPORTANT>
PRs without evidence MUST remain in DRAFT status. Never mark a PR ready for review unless:
1. Evidence is provided in the PR description, OR
2. It's a content-only PR (docs, comments, changelog)

If evidence cannot be gathered, the PR requires human QA and must be added to the action items list.
</IMPORTANT>

Keep in **draft** and add to PR description:

```markdown
## Evidence

**Cannot be tested in current environment:**
- Resource needed: Windows machine
- Reason: Fix is for Windows-specific `fcntl` import error
- Manual verification steps:
  1. Checkout this branch on Windows
  2. Run `python -c "from openhands.tools import terminal"`
  3. Verify no ModuleNotFoundError occurs
```

| Category | Examples |
|----------|----------|
| 🖥️ Platform/Environment | Windows, macOS, Python 3.13 |
| 🔑 API Keys/Credentials | Anthropic key, OAuth tokens |
| 🏗️ CI/CD Infrastructure | Jenkins server, Actions runner |
| 📊 External Services | Dataset access, staging env |

### Content-Only PRs (No Testing Needed)

These can be marked ready without evidence:
- Documentation, README, blog posts
- Comments/docstrings
- Changelog updates

---

## Part 2: Review Iteration Loop

```
┌─────────────────────────────────────────────────────────────┐
│  1. Check PR readiness requirements:                         │
│     a. Evidence in PR description? (see Part 1)              │
│     b. Unresolved review comments == 0?                      │
│     ↓                                                       │
│  2. If EITHER requirement fails:                             │
│     a. Move PR to draft (if ready)                          │
│     b. Add/update Evidence section if missing                │
│     c. Address each unresolved review comment                │
│     d. Push fixes                                           │
│     e. Reply to and resolve review threads                  │
│     f. Mark PR ready                                        │
│     g. GOTO step 1 (bot may review new code!)               │
│     ↓                                                       │
│  3. If BOTH requirements pass:                               │
│     ✓ PR is ready for human review                          │
└─────────────────────────────────────────────────────────────┘
```

<IMPORTANT>
A PR must be in DRAFT status unless BOTH conditions are met:
1. **Evidence exists**: PR description contains an `## Evidence` section with concrete proof the changes work (before/after for bugs, working demo for features), OR it's a content-only PR
2. **No unresolved reviews**: All review threads are resolved

If either condition fails, the PR MUST remain in or be moved to draft status.
</IMPORTANT>

<IMPORTANT>
After pushing fixes and resolving threads, **always re-check for new reviews**. 
Automated bots may add new comments on your fix code, creating another iteration cycle.
Continue until unresolved count is 0.
</IMPORTANT>

## Check Unresolved Review Count

```bash
gh api graphql -f query='
{
  repository(owner: "OWNER", name: "REPO") {
    pullRequest(number: PR_NUMBER) {
      reviewThreads(first: 50) {
        nodes { isResolved }
      }
    }
  }
}' | jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length'
```

## Get Unresolved Review Details

```bash
gh api graphql -f query='
{
  repository(owner: "OWNER", name: "REPO") {
    pullRequest(number: PR_NUMBER) {
      reviewThreads(first: 50) {
        nodes {
          id
          isResolved
          path
          line
          comments(first: 3) {
            nodes { 
              body 
              author { login }
            }
          }
        }
      }
    }
  }
}' | jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)'
```

## Move PR to Draft

Move a PR to draft when:
- Unresolved review comments exist, OR
- Evidence section is missing or incomplete (for non-content PRs)
```bash
# First get the PR node ID
PR_ID=$(gh api repos/OWNER/REPO/pulls/PR_NUMBER --jq '.node_id')

# Convert to draft
gh api graphql -f query="
mutation {
  convertPullRequestToDraft(input: {pullRequestId: \"$PR_ID\"}) {
    pullRequest { isDraft }
  }
}"
```

## Reply to Review Thread

After fixing an issue:
```bash
gh api graphql -f query='
mutation {
  addPullRequestReviewThreadReply(input: {
    pullRequestReviewThreadId: "THREAD_ID"
    body: "Fixed in COMMIT_SHA"
  }) {
    comment { id }
  }
}'
```

## Resolve Review Thread

```bash
gh api graphql -f query='
mutation {
  resolveReviewThread(input: {threadId: "THREAD_ID"}) {
    thread { isResolved }
  }
}'
```

## Mark PR Ready for Review

Only mark ready when BOTH conditions are satisfied:
1. Evidence section exists in PR description (or it's a content-only PR)
2. All review threads are resolved
```bash
PR_ID=$(gh api repos/OWNER/REPO/pulls/PR_NUMBER --jq '.node_id')

gh api graphql -f query="
mutation {
  markPullRequestReadyForReview(input: {pullRequestId: \"$PR_ID\"}) {
    pullRequest { isDraft }
  }
}"
```

## Batch Check Multiple PRs

Check all your ready PRs for unresolved reviews:
```bash
for pr_info in "Owner/Repo/123" "Owner2/Repo2/456"; do
  owner=$(echo $pr_info | cut -d'/' -f1)
  repo=$(echo $pr_info | cut -d'/' -f2)
  num=$(echo $pr_info | cut -d'/' -f3)
  
  unresolved=$(gh api graphql -f query="
    { repository(owner: \"$owner\", name: \"$repo\") { 
        pullRequest(number: $num) { 
          reviewThreads(first: 50) { nodes { isResolved } } 
        } 
      } 
    }" | jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length')
  
  if [ "$unresolved" != "0" ]; then
    echo "⚠️  $owner/$repo#$num: $unresolved unresolved"
  else
    echo "✅ $owner/$repo#$num: OK"
  fi
done
```

## Best Practices

1. **Always iterate**: Don't assume resolving reviews means you're done
2. **Check after marking ready**: Bots often trigger on PR status changes
3. **Reply before resolving**: Document what you did or why you declined
4. **Batch operations**: Check all PRs at once to catch issues early
5. **Track iterations**: Note how many cycles a PR took for process improvement
