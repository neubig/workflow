# Public daily-workflow example

This self-contained terminal demo replays priority-aware intake from two public
OpenHands GitHub items and one **synthetic, visibly labeled Slack fixture**. It
shows five human-in-the-loop stages: privacy inspection, intake approval, a
redirect of the agent's initial priority recommendation, bounded-action
approval, and evidence rejection/recovery.

The committed replay code and fixture are safe to publish as a **fixture-backed
development demo**. They must not be described as a recording of real Slack
content. The exact remaining blocker for a real-Slack recording is an OpenHands
message/thread with documented public-disclosure approval; see
[Privacy audit](PRIVACY-AUDIT.md).

[![Animated terminal replay](https://raw.githubusercontent.com/neubig/workflow/4c8bf65a2b1c77fc5c0313990849fa1d982dddf9/.pr/public-daily-workflow-example/live-demo.svg)](https://github.com/neubig/workflow/blob/4c8bf65a2b1c77fc5c0313990849fa1d982dddf9/.pr/public-daily-workflow-example/live-demo.svg)

The animation above is the commit-pinned, reviewed live replay from
[PR #12](https://github.com/neubig/workflow/pull/12). It is retained as
historical PR evidence; disposable `.pr/` artifacts are intentionally not part
of `main`.

## Data boundary

- GitHub records must use an exact `https://github.com/OpenHands/...` issue or
  pull-request URL. Live verification confirms the repository is public and
  owned by `OpenHands`.
- Real Slack content is rejected unless it has an approval reference, review
  date, public-recording approval, and a disclosure-safe reference. The
  committed input instead uses `slack_fixture`, contains no real message, and
  is labeled `[SYNTHETIC FIXTURE]` everywhere it is displayed.
- The CLI never reads issue/PR bodies, authors, assignees, comments, Slack
  permalinks, credentials, Linear data, or customer data. It performs no remote
  writes.

Every displayed example datum is accounted for in [SOURCE-MAP.md](SOURCE-MAP.md).

## Requirements

- Python 3.11 or newer
- Internet access for `--verify-live`
- Optional: [`uv`](https://docs.astral.sh/uv/) and the util-linux `script`
  command for recording the cast and animated SVG (`record-demo.sh` installs no
  project dependencies)

No Python packages, GitHub token, Slack token, or Linear access are required.
An optional `GH_TOKEN`/`GITHUB_TOKEN` increases GitHub API limits; the value is
used only as an HTTP header and is never printed or stored.

## Setup and interactive replay

From the repository root:

```bash
cd examples/public-daily-workflow-example
python3 demo.py --validate-only --verify-live
python3 demo.py --verify-live --report /tmp/public-daily-workflow-decision.json
```

At the prompts, inspect the source URLs and make your own decisions. A useful
recovery-path run is:

1. Approve the sanitized intake (`y`).
2. Redirect the score-only recommendation (`r`) and select the docs issue (`2`).
3. Approve the bounded, read-only action (`y`).
4. Reject publication as real Slack (`n`).
5. Approve the corrected fixture-backed evidence package (`y`).

The optional report contains only item IDs, human decisions, and the external
write count. Keep ad-hoc reports outside the repository.

## Deterministic replay and recording

The exact non-interactive command used for the timed cast/SVG evidence is:

```bash
python3 demo.py --verify-live --answers y,r,2,y,n,y --pace 0.12
```

The text transcript omits `--pace`; its decisions and output are otherwise the
same.

Refresh the text transcript, asciinema cast, animated SVG, and checksums with:

```bash
./record-demo.sh
```

The generated artifacts are genuine executions of `demo.py` through its live
GitHub-verification path. `--answers` echoes previously chosen human decisions
so the recording is reproducible; omit it for a fresh human session. The
reviewed PR #12 artifacts are available as a commit-pinned
[evidence index](https://github.com/neubig/workflow/blob/4c8bf65a2b1c77fc5c0313990849fa1d982dddf9/.pr/public-daily-workflow-example/README.md),
[cast](https://github.com/neubig/workflow/blob/4c8bf65a2b1c77fc5c0313990849fa1d982dddf9/.pr/public-daily-workflow-example/live-demo.cast),
[SVG](https://github.com/neubig/workflow/blob/4c8bf65a2b1c77fc5c0313990849fa1d982dddf9/.pr/public-daily-workflow-example/live-demo.svg),
and [transcript](https://github.com/neubig/workflow/blob/4c8bf65a2b1c77fc5c0313990849fa1d982dddf9/.pr/public-daily-workflow-example/live-demo.txt).
The `.pr/` directory is temporary reviewer context and is removed after
approval; run `record-demo.sh` to regenerate it. The source map, privacy audit,
replay code, and reproduction instructions remain with the example.

For a final real-Slack video, first replace the fixture only after obtaining the
approval fields enforced by `demo.py`, update the source map, repeat the privacy
audit, then record the same command without `--answers` using any screen
recorder. Do not record notification chrome, shell history, environment output,
or any unreviewed Slack UI.

## Automated checks

```bash
python3 demo.py --validate-only
python3 -m unittest discover -s ../../tests -p 'test_*.py'
```

The unit tests validate the policy gates; they are not live evidence. The
commit-pinned PR #12 cast, SVG, and transcript were produced with
`--verify-live` and are the reviewed live-path evidence. Newly generated
recordings remain under `.pr/` for review and do not land on `main`.
