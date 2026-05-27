# Repository Notes

- Repository root for work is `/workspace/project/workflow`.
- GitHub repository: `neubig/workflow`.
- GitHub PR iteration should use the `iterate` skill from `OpenHands/extensions`; do not maintain duplicate local PR workflow directions.
- `scripts/daily-workflow-fetch.py` should treat Linear tickets with active GitHub issue/PR links as tracked on GitHub (show direct links instead of duplicating separate Linear-only action).
- `scripts/daily-workflow-fetch.py` should exclude Linear tickets that are blocked by another active issue or labeled `Blocked`.
- Linear MCP tools are the expected interface for Linear reads/writes in workflow skills; do not document or use raw Linear API key shell calls for daily workflow triage.
- Giant Eagle product search can be automated via `https://core.shop.gianteagle.com/api/v2` using the `GetProducts` GraphQL query and `storeCode: "VIRTUAL"`; direct product links use `/grocery/search/product/{sku}`.
