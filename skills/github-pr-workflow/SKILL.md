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

### PRs That Need Evidence: TRY TO GATHER IT

<IMPORTANT>
**Your job is to TRY to gather evidence, not just report that it's missing.**

For each PR without evidence:
1. Clone the repository and checkout the PR branch
2. Read the code changes to understand what needs to be demonstrated
3. Attempt to run/test the changes to gather evidence
4. If successful, add the evidence to the PR description and mark ready
5. If you tried but FAILED, document:
   - What you tried
   - Why it failed
   - What specific resource/access is needed for human QA

Only add to action items if you genuinely cannot gather evidence after trying.
</IMPORTANT>

### When Evidence Truly Cannot Be Gathered

Keep in **draft** and add to PR description explaining what you tried:

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
│     c. CI checks passing?                                    │
│     ↓                                                       │
│  2. If ANY requirement fails:                                │
│     a. Move PR to draft (if ready)                          │
│     b. Add/update Evidence section if missing                │
│     c. Address each unresolved review comment                │
│     d. Fix CI failures                                       │
│     e. Push fixes                                           │
│     f. Reply to and resolve review threads                  │
│     g. Wait for CI to complete                              │
│     h. Mark PR ready                                        │
│     i. GOTO step 1 (bot may review new code!)               │
│     ↓                                                       │
│  3. If ALL requirements pass:                                │
│     ✓ PR is ready for human review                          │
└─────────────────────────────────────────────────────────────┘
```

<IMPORTANT>
A PR must be in DRAFT status unless ALL conditions are met:
1. **Evidence exists**: PR description contains an `## Evidence` section with concrete proof the changes work (before/after for bugs, working demo for features), OR it's a content-only PR
2. **No unresolved reviews**: All review threads are resolved
3. **CI passes**: All required CI checks are passing

If ANY condition fails, the PR MUST remain in or be moved to draft status.
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

## Check CI Status

```bash
gh pr checks OWNER/REPO --pr PR_NUMBER
```

Or via API:
```bash
gh api repos/OWNER/REPO/commits/$(gh api repos/OWNER/REPO/pulls/PR_NUMBER --jq '.head.sha')/check-runs \
  --jq '.check_runs[] | "\(.name): \(.conclusion // .status)"'
```

## Mark PR Ready for Review

Only mark ready when ALL conditions are satisfied:
1. Evidence section exists in PR description (or it's a content-only PR)
2. All review threads are resolved
3. All required CI checks are passing

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

Check all your ready PRs for unresolved reviews and CI status:
```bash
for pr_info in "Owner/Repo/123" "Owner2/Repo2/456"; do
  owner=$(echo $pr_info | cut -d'/' -f1)
  repo=$(echo $pr_info | cut -d'/' -f2)
  num=$(echo $pr_info | cut -d'/' -f3)
  
  # Check unresolved reviews
  unresolved=$(gh api graphql -f query="
    { repository(owner: \"$owner\", name: \"$repo\") { 
        pullRequest(number: $num) { 
          reviewThreads(first: 50) { nodes { isResolved } } 
        } 
      } 
    }" | jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length')
  
  # Check CI status
  ci_failed=$(gh pr checks $num --repo $owner/$repo 2>/dev/null | grep -c "fail\|error" || echo "0")
  ci_pending=$(gh pr checks $num --repo $owner/$repo 2>/dev/null | grep -c "pending\|queued" || echo "0")
  
  if [ "$unresolved" != "0" ]; then
    echo "⚠️  $owner/$repo#$num: $unresolved unresolved reviews"
  elif [ "$ci_failed" != "0" ]; then
    echo "❌ $owner/$repo#$num: CI failing"
  elif [ "$ci_pending" != "0" ]; then
    echo "⏳ $owner/$repo#$num: CI pending"
  else
    echo "✅ $owner/$repo#$num: Ready"
  fi
done
```

## Best Practices

1. **Always iterate**: Don't assume resolving reviews means you're done
2. **Wait for CI**: Always wait for CI to complete before marking ready
3. **Fix CI first**: Address CI failures before spending time on reviews (code may change)
4. **Check after marking ready**: Bots often trigger on PR status changes
5. **Reply before resolving**: Document what you did or why you declined
6. **Batch operations**: Check all PRs at once to catch issues early
7. **Track iterations**: Note how many cycles a PR took for process improvement
