# Repository Notes

- `skills/daily-workflow/scripts/daily-workflow-fetch.py` should treat Linear tickets with active GitHub issue/PR links as tracked on GitHub and show direct links instead of duplicating a Linear-only action.
- `skills/daily-workflow/scripts/daily-workflow-fetch.py` should exclude Linear tickets that are blocked by another active issue or labeled `Blocked`.
- Sprint and cycle planning must remain collaborative. Skills may gather evidence and recommend scope, but must not finalize commitments, mutate the plan, or close the planning ticket without the user's explicit approval.
- Daily-workflow skills should use `LINEAR_API_KEY` as the primary Linear credential when it is available. Keep token handling inside bundled helpers when practical, never print the credential, and use Linear MCP connections for additional workspaces or when the token is unavailable.
- Keep personal identities, internal infrastructure details, customer data, credentials, and generated workflow reports out of this public repository.

## PR-Specific Evidence

The root `.pr/` directory is temporary reviewer context. Put disposable live
evidence there—casts, screenshots, recordings, transcripts, logs, or replay
scripts that should not land on `main`. Do not put implementation, required
documentation, or the only copy of an audit/source map in `.pr/`.

The `PR Artifacts` workflow (`.github/workflows/pr-artifacts.yml`) posts one
notice when a PR contains `.pr/`. After a reviewer approves a same-repository
PR, the workflow removes `.pr/` with an automated commit. Fork authors must
remove it manually before merge.

Every `.pr/` artifact should be linked or embedded in the PR description so it
is visible to reviewers. Prefer a commit-pinned raw URL for inline images and a
commit-pinned blob URL for downloadable or text artifacts. Keep the description
clear that `.pr/` evidence is live-path evidence rather than unit-test output.
