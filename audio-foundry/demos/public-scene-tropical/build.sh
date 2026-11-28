#!/usr/bin/env bash
set -Eeuo pipefail
out="${1:?usage: build.sh OUTPUT_DIR}"
[[ ! -e "$out" ]] || { echo "refuse overwrite: $out" >&2; exit 2; }
command -v ffmpeg >/dev/null
command -v ffprobe >/dev/null
command -v go >/dev/null
command -v python3 >/dev/null
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
# Resolve output before changing working directory for the canonical Go CLI.
mkdir -p "$(dirname "$out")"
out="$(cd "$(dirname "$out")" && pwd)/$(basename "$out")"
mkdir -p "$out/stems"
trap 'echo "first failure at line $LINENO" >&2' ERR
# Original synthetic tonal/noise textures only; no species realism claim.
ffmpeg -nostdin -hide_banner -loglevel error -f lavfi -i 'anoisesrc=color=pink:sample_rate=48000:duration=12:seed=51' -af 'lowpass=f=700,volume=0.08,afade=t=in:d=1,afade=t=out:st=10.5:d=1.5' -ac 2 -c:a pcm_s16le "$out/stems/wind.wav"
ffmpeg -nostdin -hide_banner -loglevel error -f lavfi -i 'aevalsrc=0.05*sin(2*PI*(1450*t+900*t*t))*if(lt(mod(t\,1.55)\,0.18)\,1\,0):s=48000:d=12' -af 'highpass=f=800,afade=t=in:d=0.3,afade=t=out:st=11:d=1' -ac 2 -c:a pcm_s16le "$out/stems/synthetic_chirps.wav"
ffmpeg -nostdin -hide_banner -loglevel error -f lavfi -i 'aevalsrc=0.045*sin(2*PI*230*t)*if(lt(mod(t\,0.8)\,0.22)\,1\,0):s=48000:d=12' -af 'lowpass=f=600' -ac 2 -c:a pcm_s16le "$out/stems/synthetic_pulses.wav"
ffmpeg -nostdin -hide_banner -loglevel error -f lavfi -i 'anoisesrc=color=white:sample_rate=48000:duration=12:seed=73' -af 'highpass=f=4500,lowpass=f=10000,volume=0.018,afade=t=in:d=0.5,afade=t=out:st=11:d=1' -ac 2 -c:a pcm_s16le "$out/stems/insect_texture.wav"
ffmpeg -nostdin -hide_banner -loglevel error -f lavfi -i 'anoisesrc=color=brown:sample_rate=48000:duration=12:seed=19' -af 'highpass=f=180,lowpass=f=1600,volume=0.055,afade=t=in:d=0.5,afade=t=out:st=10:d=2' -ac 2 -c:a pcm_s16le "$out/stems/leaf_rustle.wav"
ffmpeg -nostdin -hide_banner -loglevel error -f lavfi -i 'anoisesrc=color=blue:sample_rate=48000:duration=12:seed=29' -af 'lowpass=f=1300,volume=0.028,afade=t=in:d=1,afade=t=out:st=10:d=2' -ac 2 -c:a pcm_s16le "$out/stems/water_texture.wav"
python3 - "$out" <<'PY'
import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]); names=[
("wind","ambience"),("synthetic_chirps","fauna"),("synthetic_pulses","foley"),
("insect_texture","ambience"),("leaf_rustle","foley"),("water_texture","ambience")]
tracks=[]
for name,category in names:
 p=root/"stems"/(name+".wav")
 tracks.append(dict(id=name,category=category,asset="stems/"+p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),start_ms=0,offset_ms=0,duration_ms=12000,gain_db=-3.0,fade_in_ms=100,fade_out_ms=100))
manifest=dict(schema="scene_audio.v1",id="tropical_synthetic_12s",classification="PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL",duration_ms=12000,sample_rate_hz=48000,channels=2,tracks=tracks,events=[dict(id="bird_event_1",track_id="synthetic_chirps",entity_id="synthetic_source",kind="synthetic_chirp",time_ms=1550,position_m=[1.0,2.0,0.0])])
(root/"scene.json").write_text(json.dumps(manifest,indent=2)+"\n")
PY
# Canonical renderer is the only production path for the manifest's track controls.
(cd "$repo/audio-foundry" && go run ./cmd/scene render -assets "$out" -manifest "$out/scene.json" -out "$out/tropical_scene.wav" > "$out/render_receipt.json")
ffmpeg -nostdin -hide_banner -loglevel error -i "$out/tropical_scene.wav" -c:a aac -b:a 160k "$out/tropical_scene.m4a"
# Change only declared track gain, leaving all source bytes and clocks identical.
witness="$(mktemp -d)"
trap 'rm -rf "$witness"' EXIT
python3 - "$out/scene.json" "$witness/scene.json" <<'PY'
import json, pathlib, sys
m=json.loads(pathlib.Path(sys.argv[1]).read_text())
for t in m["tracks"]:
    t["gain_db"] -= 6
pathlib.Path(sys.argv[2]).write_text(json.dumps(m))
PY
(cd "$repo/audio-foundry" && go run ./cmd/scene render -assets "$out" -manifest "$witness/scene.json" -out "$witness/gain.wav" > "$witness/render.json")
python3 "$repo/audio-foundry/demos/public-scene-tropical/verify.py" "$out" --gain-witness "$witness/gain.wav"
