#!/usr/bin/env bash
# G0 native binary wheel qualification; entirely disposable, no source build.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$here/results"
work="$(mktemp -d "${RUNNER_TEMP:-/tmp}/usd-r8.XXXXXXXX")"
trap 'chmod -R u+w "$work" >/dev/null 2>&1 || true; rm -rf "$work"' EXIT
arch="$(uname -m)"
case "$arch" in
 x86_64) expected="c412fa1d2a5dd0c7bc65484ffe34add8f3fc7b03510867e7e019bcaf06b76177";;
 aarch64) expected="f546816f4a565731bb9e1e8c168b074cfb3c2f44131e18e8df926baeb52a2d5e";;
 *) echo "UNSUPPORTED_NATIVE_ARCH $arch" >&2; exit 2;;
esac
python3 --version | tee "$here/results/toolchain.txt"
python3 -m venv "$work/venv"
mkdir -p "$work/wheels"
"$work/venv/bin/pip" download --disable-pip-version-check --no-deps \
  --only-binary=:all: --dest "$work/wheels" 'usd-core==26.11'
mapfile -t wheels < <(find "$work/wheels" -maxdepth 1 -type f -name 'usd_core-26.11-*.whl' -print)
test "${#wheels[@]}" -eq 1
printf '%s  %s\n' "$expected" "${wheels[0]}" | sha256sum -c -
printf '%s\n' "$expected" > "$here/results/upstream-pypi-wheel-sha256.txt"
"$work/venv/bin/pip" install --disable-pip-version-check --no-index --no-deps \
   --find-links "$work/wheels" 'usd-core==26.11'
"$work/venv/bin/python" "$here/consumer.py" create "$work/scene.usda" "$here/results/create.json"
"$work/venv/bin/python" "$here/consumer.py" verify "$work/scene.usda" "$here/results/verify.json"
cp "$work/scene.usda" "$here/results/scene.usda"
python3 "$here/independent_oracle.py" "$here/results"
echo OPENUSD_OFFICIAL_WHEEL_R8_FRESH_PROCESS_PASS
