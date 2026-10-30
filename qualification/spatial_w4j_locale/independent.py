"""Independent non-producer source clock and locale assertion; no model input."""
import json,sys
from pathlib import Path
def verify(src,out):
 d=json.loads(Path(src).read_text())
 if d["rights"]!="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC":raise ValueError("WRONG_RIGHTS")
 p=d["source_packets"]
 expected={"en-US":("m","u"),"de-DE":("m","y"),"th-TH":("m","ɯ")}
 if len(p)!=3 or {x["language"] for x in p}!=set(expected):raise ValueError("LANGUAGE_SET")
 for x in p:
  if x["origin"]!="externally_annotated":raise ValueError("INFERRED_AS_GROUND_TRUTH")
  for i,part in enumerate(x["segments"]):
   if part["ipa"]!=expected[x["language"]][i] or part["start_sample"]!=12000*i or part["end_sample"]!=12000*(i+1):
    raise ValueError("SEGMENT_SOURCE_LINGUISTICS_OR_CLOCK")
  q=next(k for k in d["languages"] if k["language"]==x["language"])
  if q["video_frames"]!=[0,6,12] or q["cue_samples"]!=[0,12000,24000]:
   raise ValueError("RATIONAL_24FPS_48K")
 result={"status":"PASS_INDEPENDENT_SOURCE_LABELS_AND_RATIONAL_TIMELINE","languages":sorted(expected),"not_a_real_audio_or_articulatory_result":True}
 Path(out).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
 print("W4J_C2_INDEPENDENT_TRILINGUAL_MANUAL_CUE_PASS")
if __name__=="__main__":verify(sys.argv[1],sys.argv[2])
