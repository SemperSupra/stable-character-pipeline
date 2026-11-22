#!/usr/bin/env bash
# Independent R5 signal-level source-edit-to-mix witness. Public synthetic audio only.
set -euo pipefail
for engine in go csound ffmpeg ffprobe python3; do
  command -v "$engine" >/dev/null || { echo "AUDIO_R5_QA_FIRST_FAILURE: missing $engine" >&2; exit 1; }
done
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
(
  cd "$ROOT/audio-foundry/editable"
  go run ./cmd/authorctl init -out "$WORK/original.json"
  go run ./cmd/authorctl edit -in "$WORK/original.json" -out "$WORK/note.json" -field 'note[0].pitch' -value 62
  go run ./cmd/authorctl edit -in "$WORK/note.json" -out "$WORK/revision.json" -field 'motor.end_hz' -value 350
  go run ./cmd/authorctl export -in "$WORK/original.json" -out "$WORK/source-original"
  go run ./cmd/authorctl export -in "$WORK/revision.json" -out "$WORK/source-revised"
  go run ./cmd/authorctl render -bundle "$WORK/source-original" -out "$WORK/stems-original"
  go run ./cmd/authorctl render -bundle "$WORK/source-revised" -out "$WORK/stems-revised"
)
(
  cd "$ROOT/audio-foundry"
  go run ./cmd/scene render -assets "$WORK/stems-original" -manifest "$WORK/stems-original/scene_audio.json" -out "$WORK/original.wav" > "$WORK/original-mix-receipt.json"
  go run ./cmd/scene render -assets "$WORK/stems-revised" -manifest "$WORK/stems-revised/scene_audio.json" -out "$WORK/revised.wav" > "$WORK/revised-mix-receipt.json"
)
python3 "$ROOT/audio-foundry/qa/verify_ab.py" --before "$WORK/original.wav" --after "$WORK/revised.wav" --receipt "$WORK/qa-receipt.json"
python3 - "$WORK/qa-receipt.json" "$WORK/original-mix-receipt.json" "$WORK/revised-mix-receipt.json" <<'PY'
import json, pathlib, sys
qa, before, after = [json.loads(pathlib.Path(p).read_text()) for p in sys.argv[1:]]
assert qa['technical_signal_check_passed'] is True
assert qa['perceptual_acceptance'] == 'NOT_TESTED'
assert qa['before']['file_sha256'] != qa['after']['file_sha256']
assert before and after  # Both independent scene renderer receipts actually emitted.
print('R5_EDIT_SOURCE_TO_TWO_RENDERED_MIXES_SIGNAL_PASS', json.dumps({
    'mix_before_sha256': qa['before']['file_sha256'],
    'mix_after_sha256': qa['after']['file_sha256'],
    'difference_rms_fraction': qa['difference_rms_fraction'],
    'perceptual_acceptance': 'NOT_TESTED', 'real_device_acceptance': 'NOT_TESTED'
}, sort_keys=True))
PY
