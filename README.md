# Workflow Skills Repository

This repository contains OpenHands skills for managing daily development workflows.

## Skills

| Skill | Description | Triggers |
|-------|-------------|----------|
| [daily-workflow](./skills/daily-workflow/SKILL.md) | Graham's daily workflow for Linear tickets and GitHub PRs | `daily workflow`, `my workflow`, `graham workflow` |
| [github-pr-workflow](./skills/github-pr-workflow/SKILL.md) | Complete PR workflow with live testing and iterative review resolution | `pr review`, `bot review`, `review iteration`, `live test` |

## Marketplaces

Custom marketplace configurations for skill discovery:

| Marketplace | Description |
|-------------|-------------|
| [default.json](./marketplaces/default.json) | Combined marketplace with all OpenHands public skills + personal workflow skills |
| [neubig.json](./marketplaces/neubig.json) | Personal workflow skills only |

## Usage

To use these skills, configure your OpenHands `marketplace_path` to point to this repository or one of the marketplace JSON files.

## Prerequisites

These skills require the following environment variables:
- `LINEAR_API_KEY` - For Linear API access
- `GITHUB_TOKEN` - For GitHub API and CLI operations

## User Configuration

The skills are configured for:
- **Linear**: `graham@openhands.dev`
- **GitHub**: `neubig`
