"""N03D-J source-evidence seam: D24 native sole traces + F1 rig-side map + pinned E stance algorithm.
Candidate detection only. No source actor body or contact is modified or declared acceptable.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
SIDES=("rest_local_x_negative","rest_local_x_positive")
ALLOWED_ACTORS=("AsterOriginal","JuniperOriginal")
D_SCHEMA="scp.n03d-g.evaluated-foot-contact-observer.v1"
F_SCHEMA="scp.n03d-f1.native-shoe-foot-weights.v1"
def fail(code):raise ValueError(code)
def hashed(path):
 return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def check_finite(x,code):
 if type(x) not in (int,float) or not math.isfinite(x):fail(code)
 return float(x)
def actor_table(rows):
 if not isinstance(rows,list) or len(rows)!=2:fail("REQUIRED_TWO_ORIGINAL_ACTORS")
 output={}
 for row in rows:
  if not isinstance(row,dict) or row.get("actor") not in ALLOWED_ACTORS or row["actor"] in output:fail("SOURCE_ACTOR_SET_DRIFT")
  output[row["actor"]]=row
 if sorted(output)!=sorted(ALLOWED_ACTORS):fail("SOURCE_ACTOR_SET_DRIFT")
 return output
def parse_partition(samples):
 if not isinstance(samples,list) or len(samples)!=143:fail("SOURCE_24HZ_143_SAMPLES_MISSING")
 out=[]
 last_t=None;last_xy=None
 for i,r in enumerate(samples):
  if not isinstance(r,dict) or set(r)!={"t_s","z_m","xy_m"}:fail("INVALID_TRACE_RECORD")
  t=check_finite(r["t_s"],"INVALID_TIME")
  z=check_finite(r["z_m"],"INVALID_GROUND_Z")
  q=r["xy_m"]
  if not isinstance(q,list) or len(q)!=2:fail("INVALID_XY")
  xy=tuple(check_finite(k,"INVALID_XY") for k in q)
  if abs(t-i/24)>1e-8 or last_t is not None and abs((t-last_t)-1/24)>1e-8:fail("CLOCK_NOT_24HZ")
  if abs(z)>3:fail("INVALID_GROUND_Z")
  if last_xy is None:
   speed=None
  else:
   speed=math.dist(xy,last_xy)*24
   if not math.isfinite(speed) or speed>50:fail("SPEED_OUT_OF_RANGE")
  out.append({"t_s":t,"z_m":z,"v_mps":speed})
  last_xy=xy;last_t=t
 return out
def reconcile(d,f,segment_module,dsha,fsha):
 if d.get("schema")!=D_SCHEMA or f.get("schema")!=F_SCHEMA:fail("SOURCE_SCHEMAS_INCOMPATIBLE")
 if not isinstance(dsha,str) or len(dsha)!=64 or not isinstance(fsha,str) or len(fsha)!=64:fail("RECEIPT_HASH_MISSING")
 if d.get("source_scene_sha256")!=f.get("source_scene_sha256"):fail("DIFFERENT_NATIVE_SOURCE_SCENES")
 if f.get("source_trace_sha256")!=dsha:fail("SHOE_SOURCE_TRACE_RECEIPT_MISMATCH")
 if d.get("sample_count_per_side")!=143 or d.get("frame_rate_hz")!=24 or d.get("side_labels")!="REST_LOCAL_X_PARTITION_NOT_VERIFIED_ANATOMICAL_SIDES":fail("SOURCE_TRACE_CLOCK_OR_LABEL")
 if not (d.get("natural_gait_accepted") is False and d.get("mvp_accepted") is False and f.get("gait_contact_accepted") is False and f.get("anatomical_side_verified") is False):fail("UNAUTHORIZED_SOURCE_ACCEPTANCE")
 actors_d=actor_table(d.get("actors"));actors_f=actor_table(f.get("actors"))
 report=[]
 for actor in ALLOWED_ACTORS:
  da,fa=actors_d[actor],actors_f[actor]
  if da.get("native_bones")!=163 or fa.get("native_163_bone_source_rig") is not True:fail("SOURCE_RIG_TOPOLOGY_CHANGED")
  data=da.get("sides"); candidate=fa.get("partitions")
  if not isinstance(data,dict) or set(data)!=set(SIDES) or not isinstance(candidate,list) or len(candidate)!=2:fail("SOURCE_PARTITION_COUNT")
  mapping={}
  for row in candidate:
   label=row.get("rest_local_partition")
   if label not in SIDES or label in mapping:fail("AMBIGUOUS_PARTITION")
   choice=row.get("candidate_rig_side")
   if not isinstance(choice,dict) or choice.get("label") not in ("L","R") or choice.get("reason")!="CANDIDATE_SOURCE_RIG_SIDE_NOT_ANATOMICAL":fail("UNQUALIFIED_RIG_SIDE")
   if check_finite(choice.get("dominance"),"INVALID_DOMINANCE")<.85:fail("LOW_SHOE_SIDE_DOMINANCE")
   mapping[label]=choice["label"]
  if set(mapping)!=set(SIDES) or set(mapping.values())!={"L","R"}:fail("NOT_ONE_TO_ONE_SOURCE_SIDE")
  feet=[]
  for part in SIDES:
   s=data[part]
   if s.get("anatomical_side_verified") is not False:fail("ANATOMICAL_SIDE_NOT_VERIFIED")
   samples=parse_partition(s.get("samples"))
   classified=segment_module.analyze(samples)
   counts={k:{"segments":v["segments"],"candidate_frames":v["raw_candidate_frames"],"physical_foot_plant_accepted":False}
      for k,v in classified["algorithms"].items()}
   feet.append({"rest_local_partition":part,"candidate_mpbf_rig_foot_side":mapping[part],
      "label_is_anatomical_side":False,"source_sole_min_z_m":min(x["z_m"] for x in samples),
      "source_shoe_centroid_max_speed_mps":max(x["v_mps"] for x in samples if x["v_mps"] is not None),
      "sole_proximity_sliding_frames":len(classified["near_ground_skate_sample_indices"]),
      "penetration_over_10mm_frames":len(classified["penetration_over_10mm_sample_indices"]),
      "algorithms":counts,"grounded_stance_accepted":False,
      "inferred_heel_or_toe_contact":False})
  report.append({"actor":actor,"source_rig_163_bones":True,"partitions":feet})
 return {"schema":"scp.n03d-j.source-bound-stance-inference.v1",
   "source_scene_sha256":d["source_scene_sha256"],
   "source_trace_sha256":dsha,"source_weight_mapping_sha256":fsha,
   "stance_algorithm_source":"N03D-E_PINNED_EXACT_PUBLIC_COMMIT",
   "samples_per_shoe_part":143,"rate_hz":24,"actors":report,
   "semantic_warning":"MOVING_MIN_SOLE_PATCH_CENTROID_IS_NOT_PERSISTENT_MATERIAL_STANCE_TRUTH",
   "status":"SOURCE_BOUND_STANCE_CANDIDATES_NOT_PHYSICAL_CONTACT",
   "actual_5bone_ik_executed":False,"physical_foot_plant_accepted":False,
   "actual_visual_critic_passed":False,"mvp_accepted":False,"release_authorized":False}
def main():
 p=argparse.ArgumentParser()
 for s in ("trace","weight-map","algorithm-path","out"):p.add_argument("--"+s,required=True)
 args=p.parse_args()
 sys.path.insert(0,str(Path(args.algorithm_path).resolve()))
 from segment import analyze
 class Seg:pass
 Seg.analyze=staticmethod(analyze)
 d=json.loads(Path(args.trace).read_text())
 f=json.loads(Path(args.weight_map).read_text())
 result=reconcile(d,f,Seg,hashed(args.trace),hashed(args.weight_map))
 Path(args.out).write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("N03D_J_ACTUAL_SOURCE_STANCE_JOIN",json.dumps({"status":result["status"],"source":result["source_scene_sha256"],"actors":[{"actor":a["actor"],"feet":[{"partition":p["rest_local_partition"],"source_foot":p["candidate_mpbf_rig_foot_side"],"segments":{k:len(v["segments"]) for k,v in p["algorithms"].items()},"max_centroid_speed_mps":p["source_shoe_centroid_max_speed_mps"]} for p in a["partitions"]]} for a in result["actors"]],"contact_accepted":False},sort_keys=True),flush=True)
if __name__=="__main__":
 try:main()
 except (ValueError,TypeError,KeyError,OSError) as e:
  print("N03D_J_SOURCE_JOIN_RED",repr(e),file=sys.stderr)
  sys.exit(12)
