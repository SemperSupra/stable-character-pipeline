#!/usr/bin/env bash
# Fixed, public-only geometry donor experiment. No secret, generated command, or arbitrary checkout input.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
work="$(mktemp -d "${RUNNER_TEMP:-/tmp}/geometry-donors.XXXXXXXX")"
cleanup() {
    # The Go module cache deliberately stores read-only immutable sources.
    # Restore write permission only within this experiment-owned disposable directory.
    chmod -R u+w "$work" >/dev/null 2>&1 || true
    if rm -rf "$work" >/dev/null 2>&1; then
        echo "TEMP_WORK_CLEANUP_PASS"
    else
        echo "TEMP_WORK_CLEANUP_INCOMPLETE" >&2
    fi
}
trap cleanup EXIT
mkdir -p "$here/results"
export GOTOOLCHAIN=go1.25.0
export GOPATH="$work/go"
export GOMODCACHE="$work/go-modcache"
export GOCACHE="$work/go-cache"

# First RED: gsdf's CPU evaluator imports its GL/GLFW backend in the current source;
# install only the needed development headers on this disposable public Ubuntu VM.
if ! pkg-config --exists gl || [ ! -f /usr/include/X11/Xlib.h ]; then
    echo "FURNISH_EPHEMERAL_OPENGL_BUILD_HEADERS"
    sudo apt-get update -qq
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
      libgl1-mesa-dev libx11-dev libxcursor-dev libxrandr-dev \
      libxinerama-dev libxi-dev libxxf86vm-dev
fi
dpkg-query -W -f='\${binary:Package}=\${Version}\\n' libgl1-mesa-dev libx11-dev libxcursor-dev libxrandr-dev libxinerama-dev libxi-dev libxxf86vm-dev \
  > "$here/results/ephemeral-gl-dev-versions.txt" 2>/dev/null || true

echo "PUBLIC_SDF_BAKEOFF_R0"
echo "host_os=$(uname -s) host_arch=$(uname -m)"
go version
git --version

fetch_exact() {
    local name="$1" remote="$2" rev="$3"
    local dst="$work/upstream/$name"
    mkdir -p "$dst"
    git -C "$dst" init -q
    git -C "$dst" remote add origin "$remote"
    git -C "$dst" -c protocol.version=2 fetch --no-tags --depth 1 origin "$rev"
    git -C "$dst" checkout --quiet --detach FETCH_HEAD
    local actual
    actual="$(git -C "$dst" rev-parse HEAD)"
    test "$actual" = "$rev"
    printf '%s %s %s\n' "$name" "$actual" "$remote" | tee "$here/results/source-$name.txt"
}

# Immutable upstream commits discovered from the public repositories on 2026-11-12.
fetch_exact sdfx https://github.com/deadsy/sdfx.git a63cfbad6c5a0fe634ee2b393e970aaa7af7b866
fetch_exact gsdf https://github.com/soypat/gsdf.git 04e60a466dcb96339511b461aa942ec790092dbc

run_consumer() {
    local donor="$1" module="$2"
    local dst="$work/consumer-$donor"
    mkdir -p "$dst"
    cp "$here/consumer-$donor/main.go" "$dst/main.go"
    (
      cd "$dst"
      go mod init "example.org/geometry-donor-bakeoff/$donor"
      go mod edit -require="$module@v0.0.0" -replace="$module=$work/upstream/$donor"
      go mod tidy
      go run . >"$here/results/$donor.json"
      go run . >"$here/results/$donor-repeat.json"
      cmp "$here/results/$donor.json" "$here/results/$donor-repeat.json"
      go version -m "$(command -v go)" >"$here/results/go-toolchain-$donor.txt" || true
    )
}

run_consumer sdfx github.com/deadsy/sdfx
run_consumer gsdf github.com/soypat/gsdf

python3 "$here/oracle.py" --root "$here"
echo "R0_ORACLE_PASS"
