# Workflow Skills

Reusable OpenHands skills for daily development workflows and related integrations.

## Skills

| Skill | Description | Triggers |
|-------|-------------|----------|
| [daily-workflow](./skills/daily-workflow/SKILL.md) | Human-in-the-loop alignment of review requests, GitHub work, Linear tickets, and Slack-derived work for the current user | `daily workflow`, `my workflow`, `work queue` |
| [cycle-planning](./skills/cycle-planning/SKILL.md) | Facilitate collaborative, human-in-the-loop Linear cycle and sprint planning | `cycle planning`, `sprint planning`, `plan the cycle` |
| [eval-with-ci](./skills/eval-with-ci/SKILL.md) | Run SDK evaluations through a GitHub Actions CI workflow | `run eval`, `evaluation`, `benchmark`, `swebench` |
| [giant-eagle](./skills/giant-eagle/SKILL.md) | Find grocery products and recipe ingredient substitutions | `giant eagle`, `grocery ingredients`, `buy ingredients`, `recipe shopping` |
| [sub-agent-delegation](./skills/sub-agent-delegation/SKILL.md) | Delegate substantial, self-contained tasks to sub-agents | `delegate task`, `sub-agent`, `spawn agent`, `parallel task` |
| [openhands-slides](./skills/openhands-slides/SKILL.md) | Create branded reveal.js presentations and export them to PDF | `create slides`, `presentation`, `slide deck`, `slides` |
| [update-todos](./skills/update-todos/SKILL.md) | Reconcile Slack, GitHub, and Linear work items | `update todos`, `reconcile work items`, `sync linear github slack` |

The daily-workflow skill packages its local helper scripts in [`skills/daily-workflow/scripts`](./skills/daily-workflow/scripts/), so they travel with the skill when it is installed.

## Marketplace

[default.json](./marketplaces/default.json) lists the public local skills alongside public OpenHands extensions. Configure your OpenHands marketplace path to this repository or that manifest.

## Privacy and credentials

Skills may read private GitHub, Linear, Slack, or cloud data only when the user has supplied authorized tool access. Keep generated daily-workflow reports local: they can contain ticket titles, PR metadata, and review-comment excerpts. Never commit credentials, report output, or exported private data.

Depending on the skill, you may need authenticated GitHub CLI access, Linear or Slack MCP tools, Google Sheets access, or `OPENHANDS_CLOUD_API_KEY`.

## License

This repository is available under the [MIT License](./LICENSE).
