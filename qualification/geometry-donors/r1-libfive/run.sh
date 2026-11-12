#!/usr/bin/env bash
# Public-safe, source-unmodified libfive C API SDK smoke on disposable Linux native hosts.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
work="$(mktemp -d "${RUNNER_TEMP:-/tmp}/libfive-r1.XXXXXXXX")"
cleanup() {
  chmod -R u+w "$work" >/dev/null 2>&1 || true
  rm -rf "$work" >/dev/null 2>&1 && echo "TEMP_WORK_CLEANUP_PASS" || echo "TEMP_WORK_CLEANUP_INCOMPLETE"
}
trap cleanup EXIT
mkdir -p "$here/results"
echo "LIBFIVE_SDK_R1 $(uname -s) $(uname -m)"
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
  build-essential cmake ninja-build pkg-config libeigen3-dev libpng-dev libboost-all-dev

mkdir -p "$work/source"
git -C "$work/source" init -q
git -C "$work/source" remote add origin https://github.com/libfive/libfive.git
git -C "$work/source" -c protocol.version=2 fetch --depth 1 --no-tags origin 918387a9220dbac2f7ab32fb35e274c6794439cf
git -C "$work/source" checkout --quiet --detach FETCH_HEAD
actual="$(git -C "$work/source" rev-parse HEAD)"
test "$actual" = "918387a9220dbac2f7ab32fb35e274c6794439cf"
echo "SOURCE_SHA=$actual" | tee "$here/results/source.txt"
cmake --version | head -1 | tee "$here/results/cmake-version.txt"
c++ --version | head -1 | tee "$here/results/compiler-version.txt"

cmake -S "$work/source" -B "$work/build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$work/sdk" \
  -DCMAKE_INSTALL_LIBDIR=lib \
  -DBUILD_STUDIO_APP=OFF -DBUILD_GUILE_BINDINGS=OFF -DBUILD_PYTHON_BINDINGS=OFF \
  -DBUILD_TESTS=OFF -DENABLE_DEBUG=OFF -DLIBFIVE_PACKED_OPCODES=OFF
cmake --build "$work/build" --parallel 2
cmake --install "$work/build"
test -f "$work/sdk/include/libfive.h"
test -f "$work/sdk/lib/libfive.so"
test -f "$work/sdk/lib/pkgconfig/libfive.pc"

# Crucial: compile a NEW consumer with only the installed SDK, never source-tree headers/libs.
mkdir -p "$work/consumer"
cp "$here/consumer.c" "$work/consumer/consumer.c"
PKG_CONFIG_PATH="$work/sdk/lib/pkgconfig" pkg-config --cflags --libs libfive \
  > "$here/results/pkg-config-flags.txt"
cc -std=c11 -Wall -Wextra -Werror -O2 \
  -I"$work/sdk/include" "$work/consumer/consumer.c" -L"$work/sdk/lib" -lfive \
  -o "$work/consumer/consumer"
LD_LIBRARY_PATH="$work/sdk/lib" "$work/consumer/consumer" \
  | tee "$here/results/libfive-c-api-smoke.txt"
ldd "$work/consumer/consumer" > "$here/results/consumer-ldd.txt"
readelf -d "$work/sdk/lib/libfive.so" > "$here/results/libfive-elf-dynamic.txt"
echo "LIBFIVE_SDK_R1_ORACLE_PASS"
