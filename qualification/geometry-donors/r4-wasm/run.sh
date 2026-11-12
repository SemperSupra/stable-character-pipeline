#!/usr/bin/env bash
# Synthetic only. Run real js/wasm binary; do not confuse cross compilation with execution.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
consumer_dir="$here/../r3-ports/consumer"
oracle_file="$here/../r3-ports/oracle/main.go"
work="$(mktemp -d "${RUNNER_TEMP:-/tmp}/geom-wasm-r4.XXXXXXXX")"
cleanup(){
  chmod -R u+w "$work" >/dev/null 2>&1 || true
  rm -rf "$work" >/dev/null 2>&1 && echo TEMP_WORK_CLEANUP_PASS || echo TEMP_WORK_CLEANUP_INCOMPLETE
}
trap cleanup EXIT
mkdir -p "$here/results"
export GOTOOLCHAIN=go1.25.0
export GOPATH="$work/go"
export GOMODCACHE="$work/modcache"
export GOCACHE="$work/cache"
go version
node --version

src="$work/source"
mkdir -p "$src"
git -C "$src" init -q
git -C "$src" remote add origin https://github.com/deadsy/sdfx.git
git -C "$src" -c protocol.version=2 fetch --depth 1 --no-tags origin a63cfbad6c5a0fe634ee2b393e970aaa7af7b866
git -C "$src" checkout --quiet --detach FETCH_HEAD
actual="$(git -C "$src" rev-parse HEAD)"
test "$actual" = a63cfbad6c5a0fe634ee2b393e970aaa7af7b866
echo "$actual" > "$here/results/source-sha.txt"
dst="$work/consumer"
mkdir -p "$dst"
cp "$consumer_dir/main.go" "$dst/main.go"
(
  cd "$dst"
  go mod init example.org/geometry-wasm-r4
  go mod edit -require=github.com/deadsy/sdfx@v0.0.0 "-replace=github.com/deadsy/sdfx=$src"
  go mod tidy
  GOOS=js GOARCH=wasm CGO_ENABLED=0 go build -trimpath -o "$work/consumer.wasm" .
)
go version -m "$work/consumer.wasm" > "$here/results/wasm-build-info.txt"
GOROOT="$(go env GOROOT)"
node_runner="$GOROOT/lib/wasm/wasm_exec_node.js"
if [ ! -f "$node_runner" ]; then echo WASM_NODE_RUNNER_NOT_FOUND >&2; exit 2; fi
node "$node_runner" "$work/consumer.wasm" > "$here/results/wasm-first.json"
node "$node_runner" "$work/consumer.wasm" > "$here/results/wasm-repeat.json"
cmp "$here/results/wasm-first.json" "$here/results/wasm-repeat.json"
go run "$oracle_file" "$here/results/wasm-first.json" > "$here/results/independent-oracle.json"
cat "$here/results/independent-oracle.json"
sha256sum "$work/consumer.wasm" | tee "$here/results/wasm-sha256.txt"
echo WASM_JS_RUNTIME_R4_ORACLE_PASS
