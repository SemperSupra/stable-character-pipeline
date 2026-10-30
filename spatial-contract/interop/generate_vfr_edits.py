"""W4g first-party, real variable-frame-rate cut-only media experiment.
Two kept source spans [0,1.5s), [2,3.5s), output 3s.
50 original PPM frames have alternating 40/80ms display intervals; an
end sentinel at 3s is deliberately excluded by ffmpeg -t 3.000.
"""
import hashlib,json,pathlib,struct,subprocess,sys,wave
from fractions import Fraction

RATE=48000
ORIGINAL_SAMPLES=192000
KEPT=((0,72000),(96000,168000))
ORIGINAL_CLICKS=(24000,48000,84000,108000,156000)
AMPLITUDES=(10000,12000,14000,16000,18000)
EXPECTED_DEST=(24000,48000,84000,132000)
DURS=tuple(40 if i%2==0 else 80 for i in range(50))
def run(*cmd):
 r=subprocess.run(cmd,capture_output=True,timeout=90)
 if r.returncode:raise RuntimeError("FIRST_FAILURE "+repr(cmd)+" "+r.stderr.decode(errors="replace")[-1500:])
 return r.stdout.decode(errors="replace")
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def audio(path,samples):
 with wave.open(str(path),"wb") as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE)
  w.writeframes(struct.pack("<"+"h"*len(samples),*samples))
def gen(root):
 root=pathlib.Path(root);root.mkdir(parents=True,exist_ok=False)
 orig=[0]*ORIGINAL_SAMPLES
 for pos,amp in zip(ORIGINAL_CLICKS,AMPLITUDES):orig[pos]=amp
 audio(root/"original_4s.wav",orig)
 edited=orig[KEPT[0][0]:KEPT[0][1]]+orig[KEPT[1][0]:KEPT[1][1]]
 assert len(edited)==144000
 audio(root/"cut_only_3s.wav",edited)
 # derive presentation timestamps from the actual duration sequence, not
 # accumulation of rounded nominal FPS. All inputs are exact milliseconds.
 pts=[];now=0
 for d in DURS:pts.append(now);now+=d
 assert now==3000
 intended=(500,1000,1750,2750)
 markers=[min(range(len(pts)),key=lambda i:abs(pts[i]-t)) for t in intended]
 assert len(set(markers))==4
 entries=["ffconcat version 1.0"]
 for i,d in enumerate(DURS):
  path=root/f"vfr_{i:02d}.ppm"
  # white frame marks cue; black otherwise. All pixels original.
  px=(b"\xff\xff\xff" if i in markers else b"\x00\x00\x00")
  path.write_bytes(b"P6\n160 90\n255\n"+px*(160*90))
  entries.extend([f"file '{path.name}'",f"duration {Fraction(d,1000)}"])
 entries.append("file 'vfr_49.ppm'")
 (root/"frames.ffconcat").write_text("\n".join(entries)+"\n")
 video=root/"vfr_video.mkv"
 master=root/"vfr_cut_master.mkv"
 run("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
  "-safe","0","-f","concat","-i",str(root/"frames.ffconcat"),
  "-t","3.000","-fps_mode","vfr","-c:v","ffv1",str(video))
 run("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
  "-i",str(video),"-i",str(root/"cut_only_3s.wav"),
  "-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","pcm_s16le",
  "-avoid_negative_ts","disabled",str(master))
 manifest=dict(schema="spatial_audio.w4g_vfr_cut_native.v1",
  source_rights="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC",
  original_sha256=sha(root/"original_4s.wav"),edited_sha256=sha(root/"cut_only_3s.wav"),
  master_sha256=sha(master),original_cues=list(ORIGINAL_CLICKS),
  original_amplitudes=list(AMPLITUDES),dropped_original_cues=[84000],
  destination_cues=list(EXPECTED_DEST),video_frame_pts_ms=pts,video_frame_durations_ms=list(DURS),
  marker_frames=markers,video_frame_count=50,audio_sample_count=144000,
  audio_hz=RATE,container_format="Matroska",video_codec="FFV1",audio_codec="PCM_S16LE",
  ffmpeg_version=run("ffmpeg","-version").splitlines()[0])
 (root/"source_manifest.json").write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n")
 print("W4G_NATIVE_VFR_EDIT_PASS frames=50 unique_delays=[40,80] original_events=5 kept=4",flush=True)
if __name__=="__main__":
 if len(sys.argv)!=2:raise SystemExit("usage: generate_vfr_edits.py NEW_DIR")
 gen(sys.argv[1])
