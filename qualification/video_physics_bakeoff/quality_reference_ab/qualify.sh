#!/usr/bin/env bash
# Fully disposable, synthetic reference-based video quality A/B qualification.
set -euo pipefail
cd "$(dirname "$0")"
: "${OUT_DIR:?Set OUT_DIR to a fresh temporary directory}"
[[ ! -e "$OUT_DIR/reference.mkv" ]] || { echo 'No overwrite of prior evidence' >&2; exit 2; }
mkdir -p "$OUT_DIR"
ffmpeg -nostdin -hide_banner -loglevel error -y -f lavfi -i 'testsrc2=size=160x120:rate=12:duration=3' -an -pix_fmt yuv420p -c:v ffv1 "$OUT_DIR/reference.mkv"
ffmpeg -nostdin -hide_banner -loglevel error -y -i "$OUT_DIR/reference.mkv" -vf 'scale=80:60:flags=area,scale=160:120:flags=neighbor' -an -c:v libx264 -preset fast -crf 35 -pix_fmt yuv420p "$OUT_DIR/baseline.mp4"
ffmpeg -nostdin -hide_banner -loglevel error -y -i "$OUT_DIR/reference.mkv" -an -c:v libx264 -preset fast -crf 24 -pix_fmt yuv420p "$OUT_DIR/candidate.mp4"
for name in baseline candidate; do
  for metric in psnr ssim; do
    ffmpeg -nostdin -hide_banner -loglevel warning -i "$OUT_DIR/$name.mp4" -i "$OUT_DIR/reference.mkv" -lavfi "$metric=stats_file=$OUT_DIR/$name.$metric" -frames:v 36 -fps_mode passthrough -an -f null - 2>"$OUT_DIR/$name.$metric.log"
  done
done
python3 "score.py" "$OUT_DIR"
python3 "hostile_test.py" "$OUT_DIR"
