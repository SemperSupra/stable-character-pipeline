#!/usr/bin/env bash
# Bounded Ubuntu 24.04/Blender 4.0.2 runtime admission.
# Public-only, original synthetic fauna/flora CI. Preserve pixel baseline 4.0.2.
set -Eeuo pipefail
mode="${1:-}"
case "$mode" in
  interchange) packages=("blender=4.0.2+dfsg-1ubuntu8" xvfb python3-numpy) ;;
  render) packages=("blender=4.0.2+dfsg-1ubuntu8" ffmpeg xvfb python3-numpy) ;;
  *) echo 'usage: install_blender_apt.sh interchange|render' >&2; exit 64 ;;
esac
if command -v blender >/dev/null 2>&1 && command -v xvfb-run >/dev/null 2>&1 && \
   { [ "$mode" != render ] || command -v ffmpeg >/dev/null 2>&1; } && \
   blender -b --python-exit-code 5 --python-expr 'import bpy,numpy; assert bpy.app.version[:3]==(4,0,2)' >/dev/null 2>&1; then
    echo 'FLORA_APT_ALREADY_QUALIFIED Blender 4.0.2 with numpy + xvfb'
    exit 0
fi
if [ "$(. /etc/os-release; printf '%s' "$VERSION_ID")" != '24.04' ]; then
    echo '::error::FLORA_APT_UNSUPPORTED_OS expected Ubuntu 24.04' >&2; exit 65
fi
base="${RUNNER_TEMP:-/tmp}/flora-blender-apt"
mkdir -p "$base"
if [ ! -f /usr/share/keyrings/ubuntu-archive-keyring.gpg ]; then
    echo '::error::FLORA_APT_MISSING_UBUNTU_KEYRING' >&2; exit 65
fi
if [ "${FLORA_APT_DRY_RUN:-0}" = '1' ]; then
    echo "FLORA_APT_DRY_RUN Ubuntu-signed packages mode=$mode version=4.0.2 mirrors=2"
    exit 0
fi
options=(-o "Dir::Etc::sourcelist=$base/flora.list" -o 'Dir::Etc::sourceparts=-' \
    -o 'Acquire::Retries=1' -o 'Acquire::http::Timeout=22' \
    -o 'Acquire::https::Timeout=22' -o 'APT::Get::Assume-Yes=true' \
    -o 'APT::Install-Recommends=false')
phase='none'
for mirror in 'http://archive.ubuntu.com/ubuntu' 'http://mirrors.edge.kernel.org/ubuntu'; do
    cat >"$base/flora.list" <<EOF
deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] $mirror noble main universe restricted multiverse
deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] $mirror noble-updates main universe restricted multiverse
deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://security.ubuntu.com/ubuntu noble-security main universe restricted multiverse
EOF
    echo "FLORA_APT_SOURCE_BEGIN mirror=$mirror mode=$mode"
    phase=update
    if ! sudo timeout --signal=TERM --kill-after=8s 90s apt-get "${options[@]}" update -qq; then
        echo "::warning::FLORA_APT_MIRROR_FAIL mirror=$mirror phase=$phase" >&2
        continue
    fi
    phase=download
    if ! sudo timeout --signal=TERM --kill-after=8s 180s apt-get "${options[@]}" install --download-only -q "${packages[@]}"; then
        echo "::warning::FLORA_APT_MIRROR_FAIL mirror=$mirror phase=$phase" >&2
        continue
    fi
    phase=configure
    if ! sudo timeout --signal=TERM --kill-after=8s 120s apt-get "${options[@]}" install --no-download -q "${packages[@]}"; then
        echo "::error::FLORA_APT_INSTALL_FAILED mirror=$mirror phase=$phase" >&2
        exit 67
    fi
    phase=validate
    command -v xvfb-run >/dev/null 2>&1 || { echo '::error::FLORA_APT_MISSING_XVFB' >&2; exit 67; }
    blender --version | head -n 2
    if ! blender -b --python-exit-code 5 --python-expr 'import bpy,numpy; assert bpy.app.version[:3]==(4,0,2); print("FLORA_APT_NATIVE_PINNED_RUNTIME_OK")'; then
        echo '::error::FLORA_APT_VERSION_OR_NUMPY_MISMATCH' >&2; exit 67
    fi
    if [ "$mode" = render ]; then
        command -v ffmpeg >/dev/null 2>&1 || { echo '::error::FLORA_APT_FFMPEG_MISSING' >&2; exit 67; }
    fi
    echo "FLORA_APT_QUALIFIED mirror=$mirror version=4.0.2 mode=$mode"
    exit 0
done
echo "::error::FLORA_APT_BOTH_MIRRORS_UNAVAILABLE mode=$mode phase=$phase" >&2
exit 68
