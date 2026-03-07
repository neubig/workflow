# Workflow Skills Repository

This repository contains OpenHands skills for managing daily development workflows and related integrations.

## Skills

| Skill | Description | Triggers |
|-------|-------------|----------|
| [daily-workflow](./skills/daily-workflow/SKILL.md) | Graham's daily workflow for Linear tickets and GitHub PRs | `daily workflow`, `my workflow`, `graham workflow` |
| [eval-with-ci](./skills/eval-with-ci/SKILL.md) | Run SDK evaluations through the GitHub Actions-based CI workflow | `run eval`, `evaluation`, `benchmark`, `swebench` |
| [github-pr-workflow](./skills/github-pr-workflow/SKILL.md) | Complete PR workflow with live testing and iterative review resolution | `pr review`, `bot review`, `review iteration`, `live test` |
| [sub-agent-delegation](./skills/sub-agent-delegation/SKILL.md) | Delegate substantial tasks to sub-agents via DelegateTool or Cloud API | `delegate task`, `sub-agent`, `spawn agent`, `parallel task` |
| [webflow](./skills/webflow/SKILL.md) | Interact with Webflow sites, CMS collections, pages, assets, and custom code | `webflow`, `webflow api`, `webflow cms`, `webflow site` |

## Marketplaces

Custom marketplace configurations for skill discovery:

| Marketplace | Description |
|-------------|-------------|
| [default.json](./marketplaces/default.json) | Combined marketplace with all OpenHands public skills and all repo-local skills |
| [neubig.json](./marketplaces/neubig.json) | Graham's workflow-focused local skills: daily workflow, PR handling, delegation, and CI evals |

## Usage

To use these skills, configure your OpenHands `marketplace_path` to point to this repository or one of the marketplace JSON files.

## Prerequisites

Depending on which skills you use, you may need the following environment variables:
- `LINEAR_API_KEY` - Linear API access for `daily-workflow`
- `GITHUB_TOKEN` - GitHub API, CLI, and workflow access for `daily-workflow`, `github-pr-workflow`, and `eval-with-ci`
- `OPENHANDS_CLOUD_API_KEY` - OpenHands Cloud API access for the remote delegation path in `sub-agent-delegation`
- `WEBFLOW_API_KEY` - Webflow Data API access for `webflow`

## User Configuration

The workflow skills are configured for:
- **Linear**: `graham@openhands.dev`
- **GitHub**: `neubig`
