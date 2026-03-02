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

This skill explains how to trigger evaluations using the OpenHands/software-agent-sdk GitHub CI system.

## Quick Start

### Via PR Label (Easiest)

Add a label to any PR in `OpenHands/software-agent-sdk`:

| Label | Instances | Use Case |
|-------|-----------|----------|
| `run-eval-1` | 1 | Quick sanity check |
| `run-eval-50` | 50 | Standard evaluation |
| `run-eval-200` | 200 | Comprehensive eval |
| `run-eval-500` | 500 | Full benchmark |

```bash
# Add label via CLI
gh pr edit <PR_NUMBER> --repo OpenHands/software-agent-sdk --add-label run-eval-50
```

### Via Manual Workflow Dispatch

1. Go to [Actions > Run Eval](https://github.com/OpenHands/software-agent-sdk/actions/workflows/run-eval.yml)
2. Click "Run workflow"
3. Configure:
   - **benchmark**: `swebench`, `gaia`, `swtbench`, `commit0`, `multiswebench`, `terminalbench`
   - **sdk_ref**: SDK version (e.g., `v1.11.5`) or branch with "Allow unreleased branches" checked
   - **eval_limit**: Number of instances
   - **model_ids**: Comma-separated model IDs (optional)

```bash
# Via CLI (requires GITHUB_TOKEN with workflow scope)
gh workflow run run-eval.yml \
  --repo OpenHands/software-agent-sdk \
  -f benchmark=swebench \
  -f sdk_ref=v1.11.5 \
  -f eval_limit=50 \
  -f allow_unreleased_branches=false
```

## Supported Benchmarks

| Benchmark | Description |
|-----------|-------------|
| `swebench` | SWE-bench Verified (default) |
| `gaia` | GAIA benchmark |
| `swtbench` | SWT-bench |
| `commit0` | Commit0 benchmark |
| `multiswebench` | Multi-repo SWE-bench |
| `swebenchmultimodal` | Multimodal SWE-bench |

## Advanced Options

| Parameter | Description |
|-----------|-------------|
| `instance_ids` | Comma-separated specific instances to run |
| `num_infer_workers` | Override default inference parallelism |
| `num_eval_workers` | Override default evaluation parallelism |
| `max_retries` | Retries per instance (default: 3) |
| `tool_preset` | `default`, `gemini`, `gpt5`, `planning` |
| `eval_branch` | Evaluation repo branch (for testing) |
| `benchmarks_branch` | Benchmarks repo branch (for testing) |

## Monitoring Results

1. **Check workflow run**: Look for "Run Eval" workflow in [Actions](https://github.com/OpenHands/software-agent-sdk/actions)
2. **PR comment**: Bot posts evaluation trigger details on the PR
3. **Results**: Dispatched to `OpenHands/evaluation` repo for execution

## Example: Testing a PR

```bash
# 1. Create PR with your changes
gh pr create --repo OpenHands/software-agent-sdk --title "My feature"

# 2. Run quick sanity check
gh pr edit <PR_NUMBER> --repo OpenHands/software-agent-sdk --add-label run-eval-1

# 3. Check workflow status
gh run list --repo OpenHands/software-agent-sdk --workflow run-eval.yml --limit 5

# 4. Watch the run
gh run watch <RUN_ID> --repo OpenHands/software-agent-sdk
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Unsupported label" | Use exact label names: `run-eval-1`, `run-eval-50`, etc. |
| "Model ID not found" | Check valid model IDs in `.github/run-eval/resolve_model_config.py` |
| "SDK reference invalid" | Use semantic version (v1.x.x) or check "Allow unreleased branches" |
| Workflow doesn't start | Ensure you have write access to the repository |
