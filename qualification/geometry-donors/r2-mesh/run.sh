#!/usr/bin/env bash
# R2 original synthetic mesh comparison, never runs user-provided commands.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
scratch="$(mktemp -d "${RUNNER_TEMP:-/tmp}/geometry-r2.XXXXXXXX")"
cleanup(){
  chmod -R u+w "$scratch" >/dev/null 2>&1 || true
  rm -rf "$scratch" >/dev/null 2>&1 && echo TEMP_WORK_CLEANUP_PASS || echo TEMP_WORK_CLEANUP_INCOMPLETE
}
trap cleanup EXIT
mkdir -p "$here/results"
export GOPATH="$scratch/go"
export GOMODCACHE="$scratch/modcache"
export GOCACHE="$scratch/gocache"
export GOTOOLCHAIN=go1.25.0

# Existing R0 observation: gsdf CPU mesh path still imports GL/GLFW CGo.
if ! pkg-config --exists gl || [ ! -f /usr/include/X11/Xlib.h ]; then
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
    libgl1-mesa-dev libx11-dev libxcursor-dev libxrandr-dev libxinerama-dev libxi-dev libxxf86vm-dev
fi
echo "R2_RUNNER $(uname -s) $(uname -m)"
go version

fetch_exact() {
  name="$1"; remote="$2"; sha="$3"
  dst="$scratch/src/$name"
  mkdir -p "$dst"
  git -C "$dst" init -q
  git -C "$dst" remote add origin "$remote"
  git -C "$dst" -c protocol.version=2 fetch --depth 1 --no-tags origin "$sha"
  git -C "$dst" checkout --quiet --detach FETCH_HEAD
  test "$(git -C "$dst" rev-parse HEAD)" = "$sha"
  printf "%s %s\n" "$name" "$sha" | tee "$here/results/source-$name.txt"
}

fetch_exact sdfx https://github.com/deadsy/sdfx.git a63cfbad6c5a0fe634ee2b393e970aaa7af7b866
fetch_exact gsdf https://github.com/soypat/gsdf.git 04e60a466dcb96339511b461aa942ec790092dbc

consumer(){
  name="$1"; module="$2"
  dest="$scratch/consumer-$name"
  mkdir -p "$dest"
  cp "$here/$name/main.go" "$dest/main.go"
  (
    cd "$dest"
    go mod init "example.org/geometry-r2-$name"
    go mod edit -require="$module@v0.0.0" -replace="$module=$scratch/src/$name"
    go mod tidy
    go build -trimpath -o "$dest/mesh" .
  )
  echo "$dest/mesh"
}
sdfx_mesh="$(consumer sdfx github.com/deadsy/sdfx | tail -1)"
gsdf_mesh="$(consumer gsdf github.com/soypat/gsdf | tail -1)"
"$sdfx_mesh" uniform "$here/results/sdfx-uniform.stl"
"$sdfx_mesh" octree "$here/results/sdfx-octree.stl"
"$gsdf_mesh" "$here/results/gsdf-flat.stl"
python3 "$here/oracle.py"
echo "R2_MESH_ORACLE_PASS"
