#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../fixtures"
mkdir -p videos
# Completely original synthetic input signals; no private media.
ffmpeg -nostdin -hide_banner -loglevel error -y -f lavfi -i 'testsrc2=size=160x120:rate=12:duration=3' -an -c:v libx264 -pix_fmt yuv420p videos/clean.mp4
ffmpeg -nostdin -hide_banner -loglevel error -y -f lavfi -i 'color=c=red:size=160x120:rate=12:duration=3' -an -c:v libx264 -pix_fmt yuv420p videos/frozen.mp4
ffmpeg -nostdin -hide_banner -loglevel error -y -f lavfi -i 'color=c=black:size=160x120:rate=12:duration=3' -an -c:v libx264 -pix_fmt yuv420p videos/black.mp4
