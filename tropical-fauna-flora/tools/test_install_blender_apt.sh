#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
helper="$here/install_blender_apt.sh"
bash -n "$helper"
set +e
output="$(bash "$helper" invalid 2>&1)"
result=$?
set -e
[ "$result" -eq 64 ] || { echo 'invalid mode was not rejected' >&2; exit 1; }
[[ "$output" == *'usage:'* ]] || { echo 'unexpected invalid-mode diagnostic' >&2; exit 1; }
grep -q 'blender=4.0.2+dfsg-1ubuntu8' "$helper"
grep -q 'signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg' "$helper"
! grep -Eq 'apt-key|trusted=yes|allow-unauthenticated' "$helper"
echo 'FLORA_APT_OFFLINE_CONTRACT_PASS'
