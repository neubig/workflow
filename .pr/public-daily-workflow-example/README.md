# Live evidence

This directory is temporary PR-only reviewer context. Each artifact is embedded
or linked in the pull request description and will be removed after approval;
the reproducible demo and its required audit documentation remain under
`examples/public-daily-workflow-example/`.

These are live-path artifacts, not unit-test output:

| Artifact | Purpose |
|---|---|
| `live-demo.svg` | Publishable animated terminal replay for GitHub/HTML viewers |
| `live-demo.cast` | Asciinema v2 terminal event stream for replay or conversion |
| `live-demo.txt` | Searchable transcript from the same command and decisions |
| `SHA256SUMS` | Integrity hashes for all three artifacts |

They were generated on 2026-07-16 by
[`record-demo.sh`](../../examples/public-daily-workflow-example/record-demo.sh),
which runs the actual CLI with live GitHub visibility checks and the recorded
human choices `y,r,2,y,n,y`. The script records asciinema v2 events and runs the
same command through `termtosvg` in a clean PTY. The run verifies both mapped
GitHub sources, redirects the agent's priority recommendation, approves a
read-only action, rejects a false real-Slack claim, and approves the corrected
fixture-backed evidence package.

The artifacts prove the workflow path and public GitHub verification. They do
not prove that a real Slack message is disclosure-approved; the fixture label
and final blocker make that limitation explicit.
