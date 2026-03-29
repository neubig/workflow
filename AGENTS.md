# Repository Notes

- Repository root for work is `/workspace/project/workflow`.
- GitHub repository: `neubig/workflow`.
- The GitHub PR iteration skill lives at `skills/github-pr-workflow/SKILL.md`.
- PR readiness rule: for non-content PRs, `## Evidence` must show a real live run (screenshot or fenced command input/output). An `## Evidence` heading alone is insufficient.
- If `## Evidence` says testing/evidence is blocked, unavailable, or still requires manual verification, the PR must remain draft and must not be marked ready for review.
- `scripts/daily-workflow-fetch.py` should treat Linear tickets with active GitHub issue/PR links as tracked on GitHub (show direct links instead of duplicating separate Linear-only action).
- `scripts/daily-workflow-fetch.py` should exclude Linear tickets that are blocked by another active issue or labeled `Blocked`.
- Linear MCP tools are available in this environment and should be preferred over raw Linear API key shell calls when the workflow only needs Linear reads/writes that MCP can perform.
