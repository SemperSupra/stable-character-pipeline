#!/usr/bin/env bash
# Source acquisition only. Never execute downloaded upstream code.
set -euo pipefail
self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$self_dir/.." && pwd)"
: "${CANDIDATE:?Set CANDIDATE from sources.tsv}"
: "${WORK_ROOT:?Set WORK_ROOT to a disposable directory}"
case "$CANDIDATE" in *[!a-zA-Z0-9_-]*|'') echo 'Invalid candidate' >&2; exit 2;; esac
row="$(awk -F '\t' -v name="$CANDIDATE" '$1==name {print; n++} END{if(n!=1) exit 2}' "$root/sources.tsv")"
IFS=$'\t' read -r id repo sha <<<"$row"
[[ "$repo" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]] || exit 2
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || exit 2
mkdir -p "$WORK_ROOT" "$root/results"
export GIT_TERMINAL_PROMPT=0 GIT_LFS_SKIP_SMUDGE=1 GIT_CONFIG_NOSYSTEM=1
repo_dir="$WORK_ROOT/$CANDIDATE"
if [[ -e "$repo_dir" ]]; then echo 'Refusing existing workset path' >&2; exit 2; fi
mkdir "$repo_dir"
cd "$repo_dir"
git init -q
git remote add origin "https://github.com/$repo.git"
timeout 90s git -c protocol.version=2 fetch -q --depth=1 --no-tags --filter=blob:none origin "$sha"
git -c advice.detachedHead=false checkout -q --detach FETCH_HEAD
actual="$(git rev-parse HEAD)"
[[ "$actual" == "$sha" ]] || { echo "Source revision drift" >&2; exit 1; }
licenses="$(find . -maxdepth 2 -type f \( -iname 'LICENSE*' -o -iname 'COPYING*' \) | wc -l | tr -d ' ')"
deps="$(find . -maxdepth 2 -type f \( -iname '*requirements*.txt' -o -iname 'pyproject.toml' -o -iname 'environment.yml' \) | wc -l | tr -d ' ')"
python3 - "$id" "$repo" "$sha" "$licenses" "$deps" "$root/results/source-$id.json" <<'PY'
import json,sys
name,repo,sha,licenses,deps,out=sys.argv[1:]
result={"schema":"scp.video-qa-source-probe.v1","candidate":name,
  "origin":"https://github.com/"+repo,"expected_commit":sha,"observed_commit":sha,
  "source_status":"ACQUIRED_PINNED","license_file_count":int(licenses),
  "dependency_manifest_count":int(deps),"installation_status":"NOT_ATTEMPTED",
  "weights_status":"NOT_ACQUIRED","inference_status":"NOT_ATTEMPTED",
  "scientific_qualification":"UNKNOWN",
  "limitations":["Source-only clone is not an installed, runnable or qualified model",
   "Git LFS and submodules excluded; controlled weight-acquisition stage pending"]}
with open(out,"w") as f:json.dump(result,f,indent=2);f.write("\n")
PY
cat "$root/results/source-$id.json"
