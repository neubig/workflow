# Source map

Audit date: 2026-07-16. Snapshot values live in `data/intake.json`; GitHub
visibility and ownership are rechecked at replay time with `--verify-live`.

| Demo record | Public source / safe reference | Exactly what is displayed | Demo-authored metadata | Why safe to publish |
|---|---|---|---|---|
| `github-pr-agent-canvas-1822` | [OpenHands/agent-canvas PR #1822](https://github.com/OpenHands/agent-canvas/pull/1822) | Repository/PR number (through the URL) and snapshot title; state and `type: fix` are retained but not rendered | Priority `High`, score `90`, and triage rationale | The repository was verified `PUBLIC` and owned by `OpenHands` on the audit date. The rationale summarizes the public snapshot/check state. No body, author, comments, branch, commits, or check URLs are stored/displayed. |
| `github-issue-docs-626` | [OpenHands/docs issue #626](https://github.com/OpenHands/docs/issues/626) | Repository/issue number (through the URL) and snapshot title; state is retained but not rendered | Priority `Medium`, score `75`, and triage rationale | The repository was verified `PUBLIC` and owned by `OpenHands` on the audit date. No body, author, comments, assignees, or linked private tracker data are stored/displayed. |
| `slack-fixture-public-demo-request` | `fixture://public-daily-workflow/slack/demo-request` | `#synthetic-public-demo` and the complete text beginning `[SYNTHETIC FIXTURE]` | Priority `Medium`, score `60`, and triage rationale | This sentence was written for this example. It contains no real Slack content, user/channel identifier, permalink, name, or private business information. The disclosure object records `contains_real_slack_content: false`. |

## Non-source workflow text

Headings, prompts, decisions, scores, rationales, PASS/BLOCKER messages, and the
bounded-action checklist are authored by this example. They describe the local
workflow and do not assert private facts. The demo does not display any other
runtime-derived fields. Live verification reports only whether each mapped URL
exists in a public repository owned by `OpenHands`, plus title/state drift when
applicable.

## Slack replacement gate

A real message must not replace the fixture until all of the following exist:

1. `type: slack` and a disclosure-safe `slack-safe://OpenHands/...` reference;
2. `status: approved_public` and `approved_for_public_demo: true`;
3. an approval reference and review date;
4. a fresh human audit of the exact displayed excerpt and recording frame; and
5. an updated row above mapping every displayed datum.

`demo.py` fails closed when any machine-checkable field is missing. Approval
itself remains a human responsibility; the schema cannot manufacture consent.
