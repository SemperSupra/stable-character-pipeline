#!/usr/bin/env bash
# Read-only source-merge simulation. No PR/branch modifications or release.
set -euo pipefail
out="${GITHUB_STEP_SUMMARY:-/dev/stdout}"
pairs=(
 "main|research/audio-capability-control-r0"
 "research/audio-capability-control-r0|experiment/audio-capability-control-reducer-r0"
 "research/audio-capability-control-r0|test/audio-control-r0-protocol-vectors"
 "experiment/audio-capability-control-reducer-r0|test/audio-control-r0-adversarial-fuzz"
 "test/audio-control-r0-adversarial-fuzz|test/audio-control-r0-crash-replay"
 "test/audio-control-r0-protocol-vectors|test/audio-control-r0-host-boundary"
 "experiment/audio-foundry-scene-contract-v01|experiment/audio-control-r0-scene-bridge"
 "experiment/audio-control-r0-scene-bridge|test/audio-control-r0-offline-recovery"
 "test/audio-control-r0-crash-replay|fix/audio-control-r0-receipt-ownership"
 "test/audio-control-r0-offline-recovery|fix/audio-control-r0-required-ffmpeg"
 "experiment/audio-capability-control-reducer-r0|experiment/audio-control-r1-recovery-ledger"
 "experiment/audio-capability-control-reducer-r0|experiment/audio-control-r1-host-admission"
)
{
 echo "## Read-only Audio Control R1 merge-tree simulation"
 echo
 echo "This is **not** merge authorization; it reports current branch-tip feasibility only."
 echo
 echo "| Base | Head | Git merge-tree | Base SHA | Head SHA |"
 echo "|---|---|---|---|---|"
} >> "$out"
for pair in "${pairs[@]}"; do
 IFS='|' read -r base head <<<"$pair"
 # Acquire the exact current ref, without updating any owner branch.
 for name in "$base" "$head"; do
  if ! git show-ref --verify --quiet "refs/remotes/origin/$name"; then
   git fetch --no-tags --quiet origin "+refs/heads/$name:refs/remotes/origin/$name"
  fi
 done
 a="refs/remotes/origin/$base"
 b="refs/remotes/origin/$head"
 shaA="$(git rev-parse "$a")"
 shaB="$(git rev-parse "$b")"
 if ! git merge-base "$shaA" "$shaB" >/dev/null; then
  status="UNKNOWN: no common ancestor"
 else
  result="$RUNNER_TEMP/audio-control-${RANDOM}-merge.txt"
  if git merge-tree --write-tree "$shaA" "$shaB" > "$result" 2>&1; then
   status="clean tree simulation"
  else
   status="NEEDS REVIEW: merge-tree nonzero"
   echo "Nonclean merge-tree for $base <- $head"
   tail -30 "$result" || true
  fi
 fi
 printf '| `%s` | `%s` | %s | `%.12s` | `%.12s` |\n' "$base" "$head" "$status" "$shaA" "$shaB" >> "$out"
 echo "$base <- $head :: $status ($shaA $shaB)"
done
echo "No remote ref, PR, tag, or release was mutated."
