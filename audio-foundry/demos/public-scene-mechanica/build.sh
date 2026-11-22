#!/usr/bin/env bash
set -Eeuo pipefail
out="${1:?usage: build.sh OUTPUT_DIR}"
[[ ! -e "$out" ]] || { echo "refuse overwrite: $out" >&2; exit 2; }
command -v ffmpeg >/dev/null
command -v ffprobe >/dev/null
mkdir -p "$out/stems"
trap 'echo "first failure at line $LINENO" >&2' ERR
# Original procedural synthetic motor and metal textures. No sampled machinery.
ffmpeg -nostdin -hide_banner -loglevel error -f lavfi -i 'anoisesrc=color=brown:sample_rate=48000:duration=12:seed=121' -af 'lowpass=f=500,volume=0.055,afade=t=in:d=0.5,afade=t=out:st=11:d=1' -ac 2 -c:a pcm_s16le "$out/stems/machine_room.wav"
ffmpeg -nostdin -hide_banner -loglevel error -f lavfi -i 'aevalsrc=0.08*sin(2*PI*(92+1.2*sin(2*PI*0.18*t))*t):s=48000:d=12' -af 'lowpass=f=420,afade=t=in:d=1,afade=t=out:st=11:d=1' -ac 2 -c:a pcm_s16le "$out/stems/motor_hum.wav"
ffmpeg -nostdin -hide_banner -loglevel error -f lavfi -i 'aevalsrc=0.07*sin(2*PI*(180+1100*mod(t\,3)/3)*t)*if(lt(mod(t\,3)\,1.1)\,1\,0):s=48000:d=12' -af 'bandpass=f=900:width_type=h:w=1500,afade=t=out:st=11:d=1' -ac 2 -c:a pcm_s16le "$out/stems/servo_sweep.wav"
ffmpeg -nostdin -hide_banner -loglevel error -f lavfi -i 'aevalsrc=0.09*sin(2*PI*1250*t)*exp(-45*mod(t\,0.6))*if(lt(mod(t\,0.6)\,0.045)\,1\,0):s=48000:d=12' -af 'highpass=f=500,lowpass=f=5000,afade=t=in:d=0.2,afade=t=out:st=11:d=1' -ac 2 -c:a pcm_s16le "$out/stems/gear_ticks.wav"
ffmpeg -nostdin -hide_banner -loglevel error -f lavfi -i 'anoisesrc=color=pink:sample_rate=48000:duration=12:seed=181' -af 'bandpass=f=1250:width_type=h:w=1800,volume=0.045,tremolo=f=5:d=0.35,afade=t=in:d=0.5,afade=t=out:st=11:d=1' -ac 2 -c:a pcm_s16le "$out/stems/hydraulic_hiss.wav"
ffmpeg -nostdin -hide_banner -loglevel error -f lavfi -i 'aevalsrc=(0.06*sin(2*PI*420*t)+0.035*sin(2*PI*910*t))*exp(-0.8*mod(t\,2))*if(lt(mod(t\,2)\,0.9)\,1\,0):s=48000:d=12' -af 'lowpass=f=2400,afade=t=in:d=0.2,afade=t=out:st=11:d=1' -ac 2 -c:a pcm_s16le "$out/stems/metal_resonance.wav"
python3 - "$out" <<'PY'
import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1]); names=[
 ("machine_room","ambience"),("motor_hum","ambience"),("servo_sweep","foley"),
 ("gear_ticks","foley"),("hydraulic_hiss","foley"),("metal_resonance","foley")]
tracks=[]
for name,category in names:
 p=root/"stems"/(name+".wav")
 tracks.append(dict(id=name,category=category,asset="stems/"+p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),start_ms=0,offset_ms=0,duration_ms=12000,gain_db=-3.0,fade_in_ms=100,fade_out_ms=100))
events=[
 dict(id="motor_start",track_id="motor_hum",entity_id="synthetic_machine",kind="synthetic_motor",time_ms=0,position_m=[0.0,0.0,0.0]),
 dict(id="servo_cycle_1",track_id="servo_sweep",entity_id="synthetic_machine",kind="synthetic_servo",time_ms=1500,position_m=[0.0,0.0,0.0]),
 dict(id="gear_tick_1",track_id="gear_ticks",entity_id="synthetic_machine",kind="synthetic_gear",time_ms=2500,position_m=[0.0,0.0,0.0]),
 dict(id="hydraulic_release",track_id="hydraulic_hiss",entity_id="synthetic_machine",kind="synthetic_hydraulic",time_ms=6000,position_m=[0.0,0.0,0.0]),
 dict(id="metal_settle",track_id="metal_resonance",entity_id="synthetic_machine",kind="synthetic_resonance",time_ms=8500,position_m=[0.0,0.0,0.0])]
manifest=dict(schema="scene_audio.v1",id="mechanica_synthetic_12s",classification="PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL",duration_ms=12000,sample_rate_hz=48000,channels=2,tracks=tracks,events=events)
(root/"scene.json").write_text(json.dumps(manifest,indent=2)+"\n")
PY
# Align and mix the six replayable stems.
ffmpeg -nostdin -hide_banner -loglevel error \
 -i "$out/stems/machine_room.wav" -i "$out/stems/motor_hum.wav" -i "$out/stems/servo_sweep.wav" \
 -i "$out/stems/gear_ticks.wav" -i "$out/stems/hydraulic_hiss.wav" -i "$out/stems/metal_resonance.wav" \
 -filter_complex '[0:a][1:a][2:a][3:a][4:a][5:a]amix=inputs=6:duration=longest:normalize=0,alimiter=limit=0.90,afade=t=out:st=11:d=1[m]' \
 -map '[m]' -t 12 -ar 48000 -ac 2 -c:a pcm_s16le "$out/mechanica_scene.wav"
ffmpeg -nostdin -hide_banner -loglevel error -i "$out/mechanica_scene.wav" -c:a aac -b:a 160k "$out/mechanica_scene.m4a"
python3 - "$out" <<'PY'
import hashlib,json,pathlib,re,subprocess,sys
root=pathlib.Path(sys.argv[1]); stem_names=["machine_room","motor_hum","servo_sweep","gear_ticks","hydraulic_hiss","metal_resonance"]
files=[root/"stems"/(n+".wav") for n in stem_names]+[root/"mechanica_scene.wav",root/"mechanica_scene.m4a"]
assets=[]
for path in files:
 meta=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_entries","stream=codec_name,sample_rate,channels","-show_entries","format=duration","-of","json",str(path)]))
 stream=meta["streams"][0]; duration=float(meta["format"]["duration"])
 assert duration>=11.98,(path,duration)
 assert int(stream["sample_rate"])==48000
 assert int(stream["channels"])==2
 expected="pcm_s16le" if path.suffix==".wav" else "aac"
 assert stream["codec_name"]==expected,(path,stream["codec_name"],expected)
 check=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-i",str(path),"-af","volumedetect","-f","null","-"],capture_output=True,text=True,check=True)
 mean=float(re.search(r"mean_volume: (-?[0-9.]+) dB",check.stderr).group(1))
 peak=float(re.search(r"max_volume: (-?[0-9.]+) dB",check.stderr).group(1))
 assert mean>-60,(path,mean)
 assert peak< -0.2,(path,peak)
 assets.append(dict(path=str(path.relative_to(root)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),duration_seconds=duration,codec=stream["codec_name"],sample_rate=int(stream["sample_rate"]),channels=int(stream["channels"]),mean_dbfs=mean,peak_dbfs=peak))
manifest=json.loads((root/"scene.json").read_text())
assert manifest["schema"]=="scene_audio.v1" and len(manifest["tracks"])==6
assert len(manifest["events"])>=5
for track in manifest["tracks"]:
 path=root/track["asset"]
 assert hashlib.sha256(path.read_bytes()).hexdigest()==track["sha256"]
receipt={"status":"per_stem_technical_signal_check_passed","perceptual_acceptance":"NOT_TESTED","real_device_acceptance":"NOT_TESTED","classification":manifest["classification"],"assets":assets}
(root/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
print("mechanica_scene_receipt_PASS stems=6 events=5 duration_seconds=12")
PY
