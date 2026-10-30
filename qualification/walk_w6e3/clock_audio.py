"""W6-E3 source-original PCM timeline for ACTUAL native W6 24f camera video.

A synthetic 48kHz clock marker, NOT speech, phonemes, heel/sole Foley,
private-person audio or anatomical synchronization acceptance.
"""
import argparse,hashlib,json,math,struct,wave
from pathlib import Path
RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
def make(folder,profile):
 if profile not in ("forward","outward"):raise ValueError("PROFILE")
 p=Path(folder)
 r=json.loads((p/"multiview_render_receipt.json").read_text())
 if r["profile"]!=profile or r["source_rights"]!=RIGHTS or r["source_frame_count"]!=24 or r["fps"]!=12:
  raise ValueError("W6E3_SOURCE_VIDEO_RIGHTS_CLOCK")
 pcm=bytearray(96000*2)
 for k in range(24):
  for t in range(48):
   sample=round(7500*(1-t/48)*(1 if k%2==0 else -1))
   struct.pack_into("<h",pcm,(k*4000+t)*2,sample)
 wav=p/"original_48k_synthetic_clock.wav"
 with wave.open(str(wav),"wb") as out:
  out.setnchannels(1);out.setsampwidth(2);out.setframerate(48000);out.writeframes(pcm)
 receipt={"schema":"scp.walk_w6e3_original_clock_sound.v1",
   "source_rights":RIGHTS,"profile":profile,"source_frames":24,
   "source_frame_rate":"12/1","output_frame_rate":"24/1",
   "audio_rate":"48000/1","source_wav_pcm_sha256":hashlib.sha256(pcm).hexdigest(),
   "pcm_samples":96000,"sample_per_motion_frame":4000,
   "source_w6_render_receipt_sha256":hashlib.sha256((p/"multiview_render_receipt.json").read_bytes()).hexdigest(),
   "source_view_mp4_sha256":{k:v["sha256"] for k,v in r["views"].items()},
   "scope":"ACTUAL_ORIGINAL_SURROGATE_VIDEO_PLUS_SYNTHETIC_MARKER_NOT_SPEECH_OR_FOLEY"}
 (p/"original_48k_clock_manifest.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
 print("W6E3_ORIGINAL_REAL_CLIP_MARKER_SOURCE_PASS",profile,receipt["source_wav_pcm_sha256"])
if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("--folder",required=True);a.add_argument("--profile",required=True)
 x=a.parse_args();make(x.folder,x.profile)
