# Privacy and disclosure audit

Audit date: 2026-07-16

Artifact status: **PASS for publication as a clearly labeled fixture-backed
development replay; NOT CLEARED for a claim that real Slack intake is shown.**

## Scope and result

| Check | Method | Result |
|---|---|---|
| GitHub organization allowlist | Schema validation requires owner `OpenHands`; live API checks confirm owner and public visibility | PASS — 2/2 mapped records |
| GitHub field minimization | Reviewed `data/intake.json`, transcript, and source map | PASS — no bodies, authors, assignees, comments, branches, commits, or private tracker fields |
| Slack disclosure | Reviewed disclosure object and every rendered fixture string | PASS — synthetic fixture only; no real message, person, channel ID, workspace ID, or permalink |
| Credentials/secrets | Automated patterns reject common GitHub/Slack tokens and email addresses; repository scan command below | PASS — none found |
| Customer/private business data | Manual review of all three displayed records and evidence frames | PASS — none present |
| Personal data | Manual review; data model deliberately excludes identity fields | PASS — no names, email addresses, avatars, or user handles displayed |
| Remote side effects | Code review and live run | PASS — GitHub calls are GET-only; external writes reported as 0 |
| Source completeness | Cross-check of data bundle, transcript, and `SOURCE-MAP.md` | PASS — every example record and displayed field is mapped |
| Recovery labeling | Live run rejects/relabels a real-Slack publication claim while the fixture is present | PASS |

## Reproduce the audit

From the repository root:

```bash
python3 examples/public-daily-workflow-example/demo.py --validate-only --verify-live
python3 -m unittest discover -s tests -p 'test_*.py'
rg -n \
  '(github_pat_|gh[opsu]_|xox[baprs]-|https://[^ ]*slack\.com/archives/|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})' \
  examples/public-daily-workflow-example/data/intake.json \
  .pr/public-daily-workflow-example/live-demo.cast \
  .pr/public-daily-workflow-example/live-demo.svg \
  .pr/public-daily-workflow-example/live-demo.txt
(cd .pr/public-daily-workflow-example && sha256sum -c SHA256SUMS)
```

The `rg` command must return no matches. A token name such as `GH_TOKEN` in the
setup documentation is not a credential value and is safe to publish.

## Pre-publication frame audit

The committed SVG and cast were inspected against this checklist:

- only the three source-map records appear;
- the Slack sentence is visibly prefixed `[SYNTHETIC FIXTURE]`;
- no desktop chrome, notifications, shell history, environment variables, or
  unrelated tabs are captured;
- the human redirect and evidence rejection/recovery are visible;
- the final frame says both `fixture-backed` and the real-Slack blocker; and
- the checksums match `.pr/public-daily-workflow-example/SHA256SUMS`.

## Exact remaining blocker

There is no authenticated, disclosure-authorized OpenHands Slack source in this
environment. Consequently no real Slack content was inspected, copied, cached,
or recorded. Completing a recording that truthfully demonstrates real Slack
intake requires an authorized reviewer to provide or verify one safe excerpt,
its disclosure-safe reference, and explicit public-recording approval. Until
then, the committed evidence is publishable only with its fixture-backed label.
