#!/usr/bin/env bash
# Read-only source feasibility review across the latest independent actor lanes.
# This deliberately never invokes git push, remote branch update or gh merge.
set -euo pipefail
pairs=(
 "research/audio-capability-control-r0|experiment/audio-control-r2-sqlite-outbox"
 "experiment/audio-control-r2-sqlite-outbox|test/audio-control-r2-sqlite-faults"
 "test/audio-control-r0-host-boundary|test/audio-control-r2-dotnet-wire"
 "fix/audio-control-r0-receipt-ownership|test/audio-control-r2-bounded-model"
 "experiment/audio-control-r1-host-admission|fix/audio-control-r1-host-stop-conformance"
 "fix/audio-control-r0-receipt-ownership|fix/audio-control-r0-required-fields"
 "experiment/audio-control-r1-recovery-ledger|test/audio-control-r1-process-restart"
 "experiment/audio-capability-control-reducer-r0|ci/audio-control-r1-selective-baseline"
)
# A missing source ref must fail the evidence gate, not be silently skipped.
fail=0
for pair in "${pairs[@]}"; do
  IFS='|' read -r base head <<<"$pair"
  for branch in "$base" "$head"; do
    if ! git ls-remote --exit-code --heads origin "refs/heads/$branch" >/dev/null; then
      echo "NOT FOUND: remote branch $branch"
      fail=1
      continue
    fi
    git fetch --no-tags --quiet origin "+refs/heads/$branch:refs/remotes/origin/$branch"
  done
  if ! git rev-parse --verify -q "refs/remotes/origin/$base" >/dev/null ||
     ! git rev-parse --verify -q "refs/remotes/origin/$head" >/dev/null; then
    fail=1
    continue
  fi
  a="$(git rev-parse "refs/remotes/origin/$base")"
  h="$(git rev-parse "refs/remotes/origin/$head")"
  output="$RUNNER_TEMP/audio-r2-merge-$RANDOM.txt"
  if git merge-tree --write-tree "$a" "$h" > "$output" 2>&1; then
    echo "CLEAN $base <- $head :: $a $h"
  else
    echo "NONCLEAN $base <- $head :: $a $h"
    tail -30 "$output"
    fail=1
  fi
done
if [ "$fail" -ne 0 ]; then
  echo "R2 source feasibility evidence NOT QUALIFIED; do not rebase/force-merge."
  exit 1
fi
echo "PASS: 8/8 R2 and local-actor parent/child edges have clean read-only Git merge trees."
echo "This is not semantic acceptance, branch-protection override or release permission."
