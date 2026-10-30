"""Independent source-only synthetic heel/toe and 12fps→48k sample proof."""
import json,math,sys
from pathlib import Path
def verify(root):
 p=Path(root);a=json.loads((p/"toy.json").read_text());b=json.loads((p/"native.json").read_text())
 for r,origin in ((a,"toy"),(b,"native")):
  if r["schema"]!="scp.w4j_a2_contact_foley.v1" or r["source"]["rights"]!="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC" or r["source"]["clock_fps"]!=12 or r["source"]["audio_hz"]!=48000 or abs(r["frozen_ground_tolerance"]-1e-4)>1e-15 or abs(r["frozen_stance_slip"]-1e-3)>1e-15:raise ValueError("CLOCK_OR_RIGHTS_INDEPENDENT_NEGATIVE")
 if b["status"]!="ABSTAIN" or b["events"] or b["source"]["foot_source"]!="NATIVE_UNLABELED_MESH" or b["source"]["frames"] or abs(b["source"]["native_min_mesh_ground_clearance"]-.2700000107)>1e-10:raise ValueError("NATIVE_UNLABELED_FOOT_MUST_ABSTAIN")
 if a["status"]!="PASS_SYNTHETIC_CONTACT_EVENTS_ONLY" or a["source"]["foot_source"]!="SOURCE_DEFINED_ARTIFICIAL_SOLE" or a["source"]["native_min_mesh_ground_clearance"]!=0:raise ValueError("TOY_SOURCE_NOT_ADMITTED")
 frames=a["source"]["frames"];previous=False;calculated=[]
 for i,f in enumerate(frames):
  if f["index"]!=i:raise ValueError("NONMONOTONIC_FRAME")
  heel,toe=f["heel"],f["toe"]
  now=(abs(heel[2])<=.0001 and abs(toe[2])<=.0001)
  if now and not previous:calculated.append({"foot_id":"OriginalToyLeft","frame":i,"sample":i*4000,"source":"EXPLICIT_SYNTHETIC_HEEL_TOE_GEOMETRY"})
  previous=now
 if calculated!=a["events"] or [e["sample"] for e in calculated]!=[4000,16000]:
  raise ValueError("EVENT_SAMPLE_CLOCK_NOT_SOURCE_DERIVED")
 out={"schema":"scp.w4j_a2_independent_oracle.v1","status":"PASS_SYNTHETIC_TOY_AND_NATIVE_ABSTAIN","events":calculated,"native_abstain":True,"scope":"NO_ANATOMICAL_FOOT_SOLE_OR_DYNAMIC_REAL_FOLEY"}
 (p/"independent.json").write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
 print("W4J_A2_INDEPENDENT_EVENT_CLOCK_PASS 2_events [4000,16000] NATIVE_ABSTAIN")
if __name__=="__main__":verify(sys.argv[1])
