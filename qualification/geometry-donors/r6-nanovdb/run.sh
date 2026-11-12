#!/usr/bin/env bash
# Pin untouched Apache-2.0 upstream source; validate a relocated header-only SDK.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$here/results"
scratch="$(mktemp -d "${RUNNER_TEMP:-/tmp}/nanovdb-r6.XXXXXXXX")"
trap 'chmod -R u+w "$scratch" >/dev/null 2>&1 || true; rm -rf "$scratch"' EXIT

revision=c2d96f735ad88a7d8e0b0a79fdd1292327ba6d36
src="$scratch/upstream"
mkdir -p "$src"
git -C "$src" init -q
git -C "$src" remote add origin https://github.com/AcademySoftwareFoundation/openvdb.git
git -C "$src" -c protocol.version=2 fetch --depth 1 --filter=blob:none --no-tags origin "$revision"
git -C "$src" checkout --quiet --detach FETCH_HEAD
test "$(git -C "$src" rev-parse HEAD)" = "$revision"
echo "$revision" > "$here/results/source-sha.txt"
c++ --version | head -1 | tee "$here/results/compiler.txt"
mkdir -p "$scratch/sdk/include"
cp -a "$src/nanovdb/nanovdb" "$scratch/sdk/include/"
cp "$src/LICENSE" "$scratch/sdk/LICENSE"
cat > "$scratch/sdk/qualification.json" <<'JSON'
{"schema":"research-sdk/v1","donor":"NanoVDB","source":"AcademySoftwareFoundation/openvdb","source_sha":"c2d96f735ad88a7d8e0b0a79fdd1292327ba6d36","profile":"CPU-header-only-read-oriented","major_serialized_grid_abi":32,"modifications":"none","redistribution":"HOLD_PENDING_REVIEW","status":"RESEARCH"}
JSON

package="$here/results/nanovdb-cpu-headers.tar.gz"
tar -C "$scratch/sdk" --sort=name --mtime='@0' --owner=0 --group=0 --numeric-owner -czf "$package" .
sha256sum "$package" | tee "$here/results/package-sha256.txt"
tar -tzf "$package" | sort > "$here/results/package-contents.txt"
test "$(grep -c 'NanoVDB.h' "$here/results/package-contents.txt")" -eq 1

# Fresh consumer: no access to original source root, only extracted SDK.
mkdir -p "$scratch/relocated" "$scratch/build"
tar -xzf "$package" -C "$scratch/relocated"
c++ -std=c++17 -O2 -Wall -Wextra -Wno-unused-parameter \
    -I"$scratch/relocated/include" "$here/consumer.cpp" -o "$scratch/build/consumer"
"$scratch/build/consumer" | tee "$here/results/oracle.txt"
echo NANOVDB_RELOCATED_CPU_SDK_R6_PASS
