# Repository Notes

- `skills/daily-workflow/scripts/daily-workflow-fetch.py` should treat Linear tickets with active GitHub issue/PR links as tracked on GitHub and show direct links instead of duplicating a Linear-only action.
- `skills/daily-workflow/scripts/daily-workflow-fetch.py` should exclude Linear tickets that are blocked by another active issue or labeled `Blocked`.
- Sprint and cycle planning must remain collaborative. Skills may gather evidence and recommend scope, but must not finalize commitments, mutate the plan, or close the planning ticket without the user's explicit approval.
- Daily-workflow skills should use Linear MCP tools for Linear reads and writes; do not add raw Linear API token shell commands to the skill instructions.
- Keep personal identities, internal infrastructure details, customer data, credentials, and generated workflow reports out of this public repository.
