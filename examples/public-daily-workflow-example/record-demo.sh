#!/usr/bin/env bash
set -euo pipefail

example_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(git -C "$example_dir" rev-parse --show-toplevel)"
evidence_dir="$repo_root/.pr/public-daily-workflow-example"
command="python3 demo.py --verify-live --answers y,r,2,y,n,y --pace 0.12"

cd "$example_dir"
mkdir -p "$evidence_dir"

python3 demo.py --verify-live --answers y,r,2,y,n,y \
  | tee "$evidence_dir/live-demo.txt"

if ! command -v uvx >/dev/null 2>&1 || ! command -v script >/dev/null 2>&1; then
  echo "uvx and the util-linux script command are required to record evidence." >&2
  exit 1
fi

uvx --from asciinema asciinema rec \
  --overwrite \
  --cols 110 \
  --rows 42 \
  --idle-time-limit 1 \
  --command "$command" \
  "$evidence_dir/live-demo.cast"

printf -v svg_command \
  'uvx termtosvg %q --command %q --screen-geometry 110x42 --template window_frame --min-frame-duration 40 --max-frame-duration 800' \
  "$evidence_dir/live-demo.svg" "$command"
# termtosvg requires a terminal; script supplies a clean PTY in headless runs.
script -qec "$svg_command" /dev/null
# Strip renderer-only provenance metadata so the artifact's GitHub URLs are
# limited to the allowlisted OpenHands demo sources.
sed -i \
  -e '/<termtosvg:template_settings /,/<\/termtosvg:template_settings>/d' \
  -e '/source: https:\/\/terminal\.sexy/d' \
  -e 's/[[:space:]]\+$//' \
  "$evidence_dir/live-demo.svg"

(
  cd "$evidence_dir"
  sha256sum live-demo.cast live-demo.svg live-demo.txt > SHA256SUMS
)

echo "Evidence refreshed in $evidence_dir"
