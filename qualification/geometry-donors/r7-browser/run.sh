#!/usr/bin/env bash
# Exact-source original CPU SDF WebAssembly running in actual headless Chromium.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$here/results"
scratch="$(mktemp -d "${RUNNER_TEMP:-/tmp}/geometry-r7.XXXXXXXX")"
server_pid=""
cleanup(){
  if [ -n "$server_pid" ]; then kill "$server_pid" >/dev/null 2>&1 || true; fi
  chmod -R u+w "$scratch" >/dev/null 2>&1 || true
  rm -rf "$scratch" >/dev/null 2>&1 && echo TEMP_WORK_CLEANUP_PASS || echo TEMP_WORK_CLEANUP_INCOMPLETE
}
trap cleanup EXIT
export GOTOOLCHAIN=go1.25.0
export GOPATH="$scratch/go"
export GOMODCACHE="$scratch/modcache"
export GOCACHE="$scratch/gocache"
export npm_config_cache="$scratch/npm-cache"
export PLAYWRIGHT_BROWSERS_PATH="$scratch/browsers"
go version | tee "$here/results/toolchain.txt"
node --version | tee -a "$here/results/toolchain.txt"
npm --version | tee -a "$here/results/toolchain.txt"
src="$scratch/src"
mkdir -p "$src"
git -C "$src" init -q
git -C "$src" remote add origin https://github.com/deadsy/sdfx.git
git -C "$src" -c protocol.version=2 fetch --no-tags --depth 1 origin a63cfbad6c5a0fe634ee2b393e970aaa7af7b866
git -C "$src" checkout --quiet --detach FETCH_HEAD
test "$(git -C "$src" rev-parse HEAD)" = a63cfbad6c5a0fe634ee2b393e970aaa7af7b866
echo a63cfbad6c5a0fe634ee2b393e970aaa7af7b866 > "$here/results/source-sha.txt"
mkdir -p "$scratch/consumer" "$scratch/web"
cp "$here/consumer/main.go" "$scratch/consumer/main.go"
cp "$here/index.html" "$scratch/web/index.html"
cp "$(go env GOROOT)/lib/wasm/wasm_exec.js" "$scratch/web/wasm_exec.js"
(
 cd "$scratch/consumer"
 go mod init example.org/geometry-browser-r7
 go mod edit -require=github.com/deadsy/sdfx@v0.0.0 "-replace=github.com/deadsy/sdfx=$src"
 go mod tidy
 GOOS=js GOARCH=wasm CGO_ENABLED=0 go build -trimpath -o "$scratch/web/consumer.wasm" .
)
test "$(od -An -tx1 -N4 "$scratch/web/consumer.wasm" | tr -d '[:space:]')" = 0061736d

npm install --prefix "$scratch/npm" --no-audit --no-fund --save-exact playwright@1.56.1
"$scratch/npm/node_modules/.bin/playwright" install --with-deps chromium
python3 -m http.server 8787 --bind 127.0.0.1 --directory "$scratch/web" > "$here/results/http-server.log" 2>&1 &
server_pid=$!
for i in {1..25}; do if curl -fsS http://127.0.0.1:8787/ >/dev/null; then break; fi; sleep 1; done
curl -fsS http://127.0.0.1:8787/ >/dev/null
node "$here/browser_oracle.cjs" "$scratch/npm" "$here/results/browser-oracle.json"
echo BROWSER_WASM_R7_ORACLE_PASS
