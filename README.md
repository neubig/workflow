# Workflow Skills Repository

This repository contains OpenHands skills for managing daily development workflows and related integrations.

## Skills

| Skill | Description | Triggers |
|-------|-------------|----------|
| [daily-workflow](./skills/daily-workflow/SKILL.md) | Human-in-the-loop alignment of open PRs, GitHub issues, Linear tickets, and Slack-derived work | `daily workflow`, `my workflow`, `graham workflow` |
| [eval-with-ci](./skills/eval-with-ci/SKILL.md) | Run SDK evaluations through the GitHub Actions-based CI workflow | `run eval`, `evaluation`, `benchmark`, `swebench` |
| [evaluate-flame-apps](./skills/evaluate-flame-apps/SKILL.md) | Score undecided FLAME cluster applications and plan 32-node GPU allocations from the shared spreadsheet | `evaluate FLAME applications`, `FLAME cluster apps`, `FLAME allocations`, `allocate FLAME GPUs` |
| [giant-eagle](./skills/giant-eagle/SKILL.md) | Find Giant Eagle grocery products and recipe ingredient substitutions using site links and the product search API | `giant eagle`, `grocery ingredients`, `buy ingredients`, `recipe shopping` |
| [sub-agent-delegation](./skills/sub-agent-delegation/SKILL.md) | Delegate substantial tasks to sub-agents via DelegateTool or Cloud API | `delegate task`, `sub-agent`, `spawn agent`, `parallel task` |
| [tunnel-to-babel](./skills/tunnel-to-babel/SKILL.md) | Start Agent Canvas backend tunnels on Babel Slurm with debug CPU or general L40S GPU jobs | `tunnel to babel`, `babel tunnel`, `slurm tunnel` |
| [openhands-slides](./skills/openhands-slides/SKILL.md) | Create branded reveal.js slide presentations with OpenHands styling and PDF export | `create slides`, `presentation`, `slide deck`, `slides` |

## Marketplaces

Custom marketplace configurations for skill discovery:

| Marketplace | Description |
|-------------|-------------|
| [default.json](./marketplaces/default.json) | Combined marketplace with all OpenHands public skills and all repo-local skills |
| [neubig.json](./marketplaces/neubig.json) | Graham's workflow-focused local skills: daily workflow, delegation, and CI evals, with PR iteration delegated to OpenHands/extensions `iterate` |

## Usage

To use these skills, configure your OpenHands `marketplace_path` to point to this repository or one of the marketplace JSON files.

## Prerequisites

Depending on which skills you use, you may need the following environment variables and tool access:
- Linear MCP tools - Linear ticket access for `daily-workflow`
- `GITHUB_TOKEN` - GitHub API, CLI, and workflow access for `daily-workflow`, external `iterate`, and `eval-with-ci`
- Google Sheets access or an exported CSV/XLSX - source application data and optional new-sheet upload for `evaluate-flame-apps`
- `OPENHANDS_CLOUD_API_KEY` - OpenHands Cloud API access for the remote delegation path in `sub-agent-delegation`

## User Configuration

The workflow skills are configured for:
- **Linear**: `graham@openhands.dev`
- **GitHub**: `neubig`
