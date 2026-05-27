---
name: eval-with-ci
description: Run evaluations using the OpenHands/software-agent-sdk CI system. Supports SWE-bench, GAIA, Terminal-Bench, and other benchmarks via GitHub Actions.
triggers:
- run eval
- evaluation
- benchmark
- swebench
- run-eval label
---

# Run Evaluations with CI

Use `OpenHands/software-agent-sdk` GitHub Actions to run evaluations.

## Trigger Options

### PR label

| Label | Instances | Use |
|-------|-----------|-----|
| `run-eval-1` | 1 | sanity check |
| `run-eval-50` | 50 | standard eval |
| `run-eval-200` | 200 | comprehensive eval |
| `run-eval-500` | 500 | full benchmark |

```bash
gh pr edit <PR_NUMBER> --repo OpenHands/software-agent-sdk --add-label run-eval-50
```

### Manual workflow dispatch

Actions → [Run Eval](https://github.com/OpenHands/software-agent-sdk/actions/workflows/run-eval.yml) → “Run workflow”, or CLI:

```bash
gh workflow run run-eval.yml \
  --repo OpenHands/software-agent-sdk \
  -f benchmark=swebench \
  -f sdk_ref=v1.11.5 \
  -f eval_limit=50 \
  -f allow_unreleased_branches=false
```

Fields: `benchmark` (`swebench`, `gaia`, `swtbench`, `commit0`, `multiswebench`, `terminalbench`), `sdk_ref` (version or branch; branch requires `allow_unreleased_branches=true`), `eval_limit`, optional `model_ids`.

## Benchmarks and Options

Supported: `swebench` (default SWE-bench Verified), `gaia`, `swtbench`, `commit0`, `multiswebench`, `swebenchmultimodal`, `terminalbench`.

Advanced fields: `instance_ids` (comma-separated), `num_infer_workers`, `num_eval_workers`, `max_retries` (default 3), `tool_preset` (`default`, `gemini`, `gpt5`, `planning`), `eval_branch`, `benchmarks_branch`.

## Monitor

```bash
gh run list --repo OpenHands/software-agent-sdk --workflow run-eval.yml --limit 5
gh run watch <RUN_ID> --repo OpenHands/software-agent-sdk
```

The PR gets a bot comment with trigger details; actual eval execution is dispatched to `OpenHands/evaluation`.

## Example PR Flow

```bash
gh pr create --repo OpenHands/software-agent-sdk --title "My feature"
gh pr edit <PR_NUMBER> --repo OpenHands/software-agent-sdk --add-label run-eval-1
gh run list --repo OpenHands/software-agent-sdk --workflow run-eval.yml --limit 5
gh run watch <RUN_ID> --repo OpenHands/software-agent-sdk
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Unsupported label | Use exact `run-eval-1/50/200/500`. |
| Model ID not found | Check `.github/run-eval/resolve_model_config.py`. |
| SDK reference invalid | Use `v1.x.x` or allow unreleased branches. |
| Workflow does not start | Confirm repo write access / workflow-scoped token. |
