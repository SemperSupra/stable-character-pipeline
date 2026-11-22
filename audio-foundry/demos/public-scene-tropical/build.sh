#!/usr/bin/env bash
set -Eeuo pipefail
out="${1:?usage: build.sh OUTPUT_DIR}"
[[ ! -e "$out" ]] || { echo "refuse overwrite: $out" >&2; exit 2; }
command -v ffmpeg >/dev/null
command -v ffprobe >/dev/null
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
manifest=dict(schema="scene_audio.v1",id="tropical_synthetic_12s",classification="PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL",duration_ms=12000,sample_rate_hz=48000,channels=2,tracks=tracks,events=[dict(id="bird_event_1",track_id="synthetic_chirps",entity_id="synthetic_source",kind="synthetic_chirp",time_ms=1700,position_m=[1.0,2.0,0.0])])
(root/"scene.json").write_text(json.dumps(manifest,indent=2)+"\n")
PY
# Align and mix the six replayable stems.
ffmpeg -nostdin -hide_banner -loglevel error \
 -i "$out/stems/wind.wav" -i "$out/stems/synthetic_chirps.wav" -i "$out/stems/synthetic_pulses.wav" \
 -i "$out/stems/insect_texture.wav" -i "$out/stems/leaf_rustle.wav" -i "$out/stems/water_texture.wav" \
 -filter_complex '[0:a][1:a][2:a][3:a][4:a][5:a]amix=inputs=6:duration=longest:normalize=0,alimiter=limit=0.92,afade=t=out:st=11:d=1[m]' \
 -map '[m]' -t 12 -ar 48000 -ac 2 -c:a pcm_s16le "$out/tropical_scene.wav"
ffmpeg -nostdin -hide_banner -loglevel error -i "$out/tropical_scene.wav" -c:a aac -b:a 160k "$out/tropical_scene.m4a"
python3 - "$out" <<'PY'
import hashlib,json,pathlib,subprocess,sys
r=pathlib.Path(sys.argv[1]); files=[r/"stems"/(n+".wav") for n in ["wind","synthetic_chirps","synthetic_pulses","insect_texture","leaf_rustle","water_texture"]]+[r/"tropical_scene.wav",r/"tropical_scene.m4a"]
receipts=[]
for p in files:
 q=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_entries","stream=codec_name,sample_rate,channels","-show_entries","format=duration","-of","json",str(p)]))
 a=q["streams"][0]; d=float(q["format"]["duration"])
 assert d>=11.98,(p,d)
 assert int(a.get("sample_rate",48000))==48000
 assert int(a.get("channels",2))==2
 if p.suffix==".wav": assert a["codec_name"]=="pcm_s16le"
 if p.suffix==".m4a": assert a["codec_name"]=="aac"
 if p.name=="tropical_scene.wav":
  v=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-i",str(p),"-af","volumedetect","-f","null","-"],capture_output=True,text=True,check=True)
  import re
  mean=float(re.search(r"mean_volume: (-?[0-9.]+) dB",v.stderr).group(1))
  peak=float(re.search(r"max_volume: (-?[0-9.]+) dB",v.stderr).group(1))
  assert mean>-60 and peak< -0.2,(mean,peak)
  receipts.append(dict(path=p.name,mean_dbfs=mean,peak_dbfs=peak))
 receipts.append(dict(path=str(p.relative_to(r)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),duration_seconds=d,codec=a["codec_name"],sample_rate=int(a.get("sample_rate",48000)),channels=int(a.get("channels",2))))
(r/"receipt.json").write_text(json.dumps({"status":"technical_signal_check_passed","perceptual_acceptance":"NOT_TESTED","real_device_acceptance":"NOT_TESTED","assets":receipts},indent=2)+"\n")
print("tropical_scene_receipt_PASS stems=6 duration_seconds=12")
PY
