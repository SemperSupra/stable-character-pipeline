#!/usr/bin/env bash
# Public original-synthetic H264 pixel mutation; no protected actor data.
set -euo pipefail
test "$#" = 3
source_mp4="$1"
mutant_mp4="$2"
source_trace="$3"
test ! -e "$mutant_mp4"
python3 - "$source_trace" <<'PY'
import json,hashlib,sys
raw=open(sys.argv[1],"rb").read()
assert hashlib.sha256(raw).hexdigest()=="1e56d63873b83dc33ea8f510932d1df0e09acfc66e9dae8880f2ae91658d5e86"
j=json.loads(raw)
assert j["source_class"]=="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
assert j["private_r009"]=="HELD_NOT_ACCEPTED"
assert j["frame_count"]==72 and j["fps"]==12
PY
ffmpeg -hide_banner -loglevel error -i "$source_mp4" -an \
 -vf "drawbox=x=260:y=50:w=112:h=128:color=black:t=fill:enable='between(t,2.999,3.001)'" \
 -c:v libx264 -crf 18 -pix_fmt yuv420p -fps_mode passthrough "$mutant_mp4"
test "$(ffprobe -v error -select_streams v:0 -count_frames -show_entries stream=nb_read_frames -of csv=p=0 "$mutant_mp4")" = 72
test "$(sha256sum "$source_mp4" | cut -d' ' -f1)" != "$(sha256sum "$mutant_mp4" | cut -d' ' -f1)"
