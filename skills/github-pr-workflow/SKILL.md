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

## PR Description Structure

<IMPORTANT>
**Every PR description MUST have these sections in this exact order:**

```markdown
## Summary
Short summary of what the PR does and what issue it resolves.
Closes #XXX

## Details
Design decisions, architecture choices, or context not obvious from code.
(Can be omitted for trivial PRs like typo fixes)

## Testing
Unit/integration tests implemented and their results.
- List of test files added/modified
- Test run output showing all tests pass

## Evidence
END-TO-END demonstration that the feature/fix works in realistic conditions.
- Command-line output, screenshots, or logs showing real behavior
- NO mention of unit tests here - this is about live functionality

## Checklist
- [ ] Tests pass
- [ ] Evidence gathered from live run
- [ ] No unnecessary code
- [ ] Documentation updated (if applicable)
```

**Key distinction:**
- `## Testing` = Unit tests implemented and passing (code verification)
- `## Evidence` = Live run showing feature works end-to-end (behavior verification)
</IMPORTANT>

## PR Readiness Checklist

<IMPORTANT>
**A PR can ONLY be marked ready for review when ALL of the following are true:**

### Required Conditions
- [ ] **Structure**: PR description has all required sections (Summary, Details, Testing, Evidence, Checklist)
- [ ] **Evidence**: Evidence section shows END-TO-END proof (no unit test mentions)
- [ ] **Reviews**: All review threads are resolved (0 unresolved)
- [ ] **CI**: All required CI checks are passing
- [ ] **Conflicts**: No merge conflicts (mergeable=true)
- [ ] **Code Quality**: No extra unnecessary code (see Part 3)
- [ ] **Tests**: Only minimal tests for core functionality (see Part 3)
</IMPORTANT>

## Part 1: Live Testing Requirements (Evidence)

<IMPORTANT>
Unit tests are NOT sufficient for the Evidence section. PRs must demonstrate actual end-to-end behavior in a live setting before being marked ready for review.

The Evidence section must show the code running in realistic conditions - a user invoking the feature, a server responding to requests, a CLI command producing expected output, etc.
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
- Comments/docstrings
- Changelog updates
- Pure prose (blog posts, announcements)

### Documentation & Skills PRs (Evidence Required)

Skills and documentation that contain **instructions or workflows** need evidence that the instructions actually work:

```markdown
## Evidence

**Verified workflow works:**
```
$ LINEAR_API_KEY="$LINEAR_API_KEY" python workflow/scripts/daily-workflow-fetch.py
Fetching Linear tickets...
  Found 33 tickets
✓ Script executed successfully
```
```

This ensures users won't follow broken instructions.

---

## Part 2: Review Iteration Loop

```
┌─────────────────────────────────────────────────────────────┐
│  1. Check PR readiness requirements:                         │
│     a. Evidence in PR description? (see Part 1)              │
│     b. Unresolved review comments == 0?                      │
│     c. CI checks passing?                                    │
│     d. No merge conflicts?                                   │
│     ↓                                                       │
│  2. If ANY requirement fails:                                │
│     a. Move PR to draft (if ready)                          │
│     b. Add/update Evidence section if missing                │
│     c. Address each unresolved review comment                │
│     d. Fix CI failures                                       │
│     e. Resolve merge conflicts (rebase or merge from base)   │
│     f. Push fixes                                           │
│     g. Reply to and resolve review threads                  │
│     h. Wait for CI to complete                              │
│     i. Mark PR ready                                        │
│     j. GOTO step 1 (bot may review new code!)               │
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
4. **No merge conflicts**: The PR can be cleanly merged into the base branch

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

## Check for Merge Conflicts

```bash
gh api repos/OWNER/REPO/pulls/PR_NUMBER --jq '.mergeable_state, .mergeable'
```

- `mergeable: true` and `mergeable_state: "clean"` = No conflicts
- `mergeable: false` or `mergeable_state: "dirty"` = Has conflicts that must be resolved

## Resolve Merge Conflicts

When a PR has merge conflicts, resolve them by rebasing or merging:

```bash
# Fetch latest changes
git fetch origin

# Option 1: Rebase onto base branch (preferred for clean history)
git checkout pr-branch
git rebase origin/main
# Resolve any conflicts manually, then:
git add .
git rebase --continue
git push --force-with-lease origin pr-branch

# Option 2: Merge base branch into PR branch
git checkout pr-branch
git merge origin/main
# Resolve any conflicts manually, then:
git add .
git commit -m "Merge main to resolve conflicts"
git push origin pr-branch
```

<IMPORTANT>
After resolving merge conflicts, CI will re-run. Always wait for CI to complete before marking the PR ready for review.
</IMPORTANT>

## Mark PR Ready for Review

Only mark ready when ALL conditions are satisfied:
1. Evidence section exists in PR description (or it's a content-only PR)
2. All review threads are resolved
3. All required CI checks are passing
4. No merge conflicts exist

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

Check all your ready PRs for unresolved reviews, CI status, and merge conflicts:
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
  
  # Check for merge conflicts
  mergeable=$(gh api repos/$owner/$repo/pulls/$num --jq '.mergeable // "unknown"' 2>/dev/null)
  
  if [ "$unresolved" != "0" ]; then
    echo "⚠️  $owner/$repo#$num: $unresolved unresolved reviews"
  elif [ "$mergeable" = "false" ]; then
    echo "🔀 $owner/$repo#$num: Has merge conflicts"
  elif [ "$ci_failed" != "0" ]; then
    echo "❌ $owner/$repo#$num: CI failing"
  elif [ "$ci_pending" != "0" ]; then
    echo "⏳ $owner/$repo#$num: CI pending"
  else
    echo "✅ $owner/$repo#$num: Ready"
  fi
done
```

## Part 3: Code Quality and Minimal Tests

<IMPORTANT>
Before marking a PR ready, review the changes for unnecessary code and excessive tests.
</IMPORTANT>

### No Extra Unnecessary Code

Check that the PR does not include:
- Dead code or commented-out code that should be removed
- Debug statements (print, console.log, debugger) left in production code
- Unused imports, variables, or functions
- Over-engineered solutions when simpler approaches exist
- Duplicated logic that could be refactored

```bash
# Quick checks for common issues
git diff main...HEAD --name-only | xargs grep -l "console.log\|print(\|debugger\|TODO\|FIXME" 2>/dev/null
```

### Minimal Tests for Core Functionality

Tests should verify core functionality, not exhaustively cover every edge case. Check that:

1. **Tests are focused**: Each test verifies ONE behavior
2. **Tests are minimal**: Only enough tests to verify the core functionality works
3. **No redundant tests**: Multiple tests shouldn't verify the same thing
4. **No excessive mocking**: Tests should exercise real code paths where possible

**Red flags for excessive testing:**
- More lines of test code than implementation code (for simple features)
- Multiple tests that differ only by input values when one parameterized test would suffice
- Tests for trivial getters/setters or obvious behavior
- Heavy mocking that obscures what's actually being tested

**Good test coverage:**
- Happy path works
- Key error conditions are handled
- Critical edge cases are covered

```markdown
## Testing

**Core functionality verified:**
- ✓ Feature works with valid input
- ✓ Returns appropriate error for invalid input
- ✓ Handles empty/null edge case

**Not tested (intentionally):**
- Trivial variations of valid input
- UI styling details
- Third-party library behavior
```

## Best Practices

1. **Always iterate**: Don't assume resolving reviews means you're done
2. **Wait for CI**: Always wait for CI to complete before marking ready
3. **Fix CI first**: Address CI failures before spending time on reviews (code may change)
4. **Resolve conflicts promptly**: Fix merge conflicts as soon as they appear to avoid complex rebases
5. **Check after marking ready**: Bots often trigger on PR status changes
6. **Reply before resolving**: Document what you did or why you declined
7. **Batch operations**: Check all PRs at once to catch issues early
8. **Track iterations**: Note how many cycles a PR took for process improvement
9. **Review for bloat**: Check for unnecessary code and excessive tests before marking ready

## Waiting for CI After Pushing Fixes

<IMPORTANT>
**After pushing a fix, wait at least 5 minutes before checking CI status again.**

CI pipelines take time to run. Do NOT immediately mark a PR ready after pushing - wait for CI to complete:

1. Push your fix
2. Wait 5 minutes (or use `sleep 300`)
3. Check CI status: `gh pr checks REPO --pr NUMBER`
4. If still pending, wait another 2-3 minutes
5. Only mark ready once ALL CI checks show pass/fail status (not pending)

```bash
# After pushing a fix, wait and verify CI
git push origin branch-name
echo "Waiting 5 minutes for CI..."
sleep 300
gh pr checks $num --repo $owner/$repo
# If all passing, then mark ready
```
</IMPORTANT>
