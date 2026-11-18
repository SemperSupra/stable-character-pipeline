import json,sys
from pathlib import Path
def run(a,b):
 if a["schema"]!=b["schema"] or a["schema"]!="scp.r090.72f-real-shoe-contact.v1":raise ValueError("SCHEMA_MISMATCH")
 if (a["mode"],b["mode"])!=("authored","recorded"):raise ValueError("WRONG_COMPARISON_ORDER")
 if a["wardrobe_base_sha256"]!=b["wardrobe_base_sha256"] or a["fps"]!=b["fps"] or a["frames"]!=b["frames"]:raise ValueError("WRONG_SOURCE_OR_CLOCK")
 out=[]
 for x,y in zip(a["actors"],b["actors"]):
  if x["actor"]!=y["actor"] or x["shoe"]!=y["shoe"]:raise ValueError("WRONG_SHOE_ASSET")
  feet=[]
  for side in ("rest_local_x_negative","rest_local_x_positive"):
   orig=x["rest_local_x_partitions"][side];new=y["rest_local_x_partitions"][side]
   feet.append({"side_partition_static_rest_local_x":side,
    "authored_penetration_m":orig["penetration_m"],"recorded_penetration_m":new["penetration_m"],
    "penetration_delta_m":round(new["penetration_m"]-orig["penetration_m"],6),
    "authored_slip_mps":orig["maximum_contact_slip_m_per_s"],"recorded_slip_mps":new["maximum_contact_slip_m_per_s"],
    "authored_near_ground_frames":orig["contact_frames"],"recorded_near_ground_frames":new["contact_frames"],
    "recorded_flags":new["flags"]})
  out.append({"actor":x["actor"],"feet":feet})
 return {"schema":"scp.r090.measured-sole-gait-bakeoff.v1","actors":out,
   "admission":"MEASURED_CONTACT_DIAGNOSTIC_NOT_GAIT_ACCEPTED","visual_critic_passed":False,
   "natural_gait_accepted":False,"mvp_accepted":False}
if __name__=="__main__":
 a,b,out=sys.argv[1:4];v=run(json.loads(Path(a).read_text()),json.loads(Path(b).read_text()))
 Path(out).write_text(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("R090_REAL_CONTACT_BAKEOFF",json.dumps(v,sort_keys=True,allow_nan=False),flush=True)
