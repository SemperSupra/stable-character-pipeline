"""Actual source-bound recorded 24Hz CC0 shoe proxy minimum static-anchor movement bounds."""
import argparse,hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from minimax import enclosing_disk
def require(q,why):
 if not q:raise ValueError(why)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--trace",required=True);p.add_argument("--out",required=True)
 a=p.parse_args()
 raw=Path(a.trace).read_bytes();t=json.loads(raw)
 require(t.get("schema")=="scp.n03d-g.evaluated-foot-contact-observer.v1" and t.get("source_class")=="ORIGINAL_FICTIONAL_CC0","SOURCE_TRACE_NOT_AUTHORIZED")
 require(t.get("frame_rate_hz")==24 and t.get("sample_count_per_side")==143,"SOURCE_CLOCK_CHANGED")
 require(sorted(x["actor"] for x in t["actors"])==["AsterOriginal","JuniperOriginal"],"ACTUAL_SOURCE_ACTOR_SET_WRONG")
 reports=[]
 for actor in t["actors"]:
  side_data={}
  require(set(actor["sides"])=={"rest_local_x_negative","rest_local_x_positive"},"SOURCE_SIDE_SET_DRIFT")
  for side,v in actor["sides"].items():
   src=v["samples"];require(len(src)==143,"SOURCE_SAMPLE_COUNT_CHANGED")
   windows=[]
   for start in range(0,131,12):
    segment=src[start:start+13]
    require(len(segment)==13 and all(abs(x["t_s"]-(start+i)/24)<1e-7 for i,x in enumerate(segment)),"TIMEBASE_OR_WINDOW_BAD")
    points=[x["xy_m"] for x in segment]
    disk=enclosing_disk(points)
    minz=min(x["z_m"] for x in segment);maxz=max(x["z_m"] for x in segment)
    # Note: stationary anchor is only a hypothetical contact label,
    # since all three source-based stance segmenters previously found none.
    windows.append({"frame_native_start":start/2.,"frame_native_end":(start+12)/2.,
      "lower_bound_source_support_immobility_radius_m":disk["minimax_radius_m"],
      "best_fixed_world_xy_m":disk["center_xy_m"],
      "support_min_z_m":round(minz,6),"support_max_z_m":round(maxz,6),
      "required_vertical_span_m":round(maxz-minz,6),
      "hypothetical_40mm_xy_correction_feasible":disk["minimax_radius_m"]<=.04,
      "actual_stance_evidence":False,"fixed_world_foot_contact_accepted":False})
   sensitivity=[]
   for length in (4,7,10,13):
    sampled=[]
    for start in range(0,144-length,6):
     seq=src[start:start+length]
     require(len(seq)==length and all(abs(x["t_s"]-(start+i)/24)<1e-7 for i,x in enumerate(seq)),"SUBWINDOW_CLOCK_DRIFT")
     fit=enclosing_disk([x["xy_m"] for x in seq])
     sampled.append(fit["minimax_radius_m"])
    sensitivity.append({"samples":length,"duration_seconds":round((length-1)/24,6),
       "stride_samples":6,"windows":len(sampled),
       "minimum_mincircle_radius_m":round(min(sampled),9),
       "maximum_mincircle_radius_m":round(max(sampled),9),
       "windows_at_most_40mm":sum(1 for x in sampled if x<=.04),
       "windows_at_most_80mm":sum(1 for x in sampled if x<=.08),
       "all_are_hypotheses_not_stance":True})
   side_data[side]={"duration_sensitivity":sensitivity,"window_count":len(windows),
    "source_minimax_radius_m":min(x["lower_bound_source_support_immobility_radius_m"] for x in windows),
    "source_maximax_radius_m":max(x["lower_bound_source_support_immobility_radius_m"] for x in windows),
    "windows":windows}
  reports.append({"actor":actor["actor"],"sides":side_data})
 result={"schema":"scp.n03d-f3.exhaustive-2d-static-contact-feasibility.v1",
  "source_trace_sha256":hashlib.sha256(raw).hexdigest(),
  "source_scene_sha256":t["source_scene_sha256"],
  "observed_frames":143,"sample_rate_hz":24,"window_samples":13,
  "actor_results":reports,"cannot_infer_stance_from_planar_support_proxy":True,
  "source_toe_heel_contact_verified":False,"physical_planted_foot_accepted":False,
  "mvp_accepted":False,"release_authorized":False}
 Path(a.out).write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+chr(10))
 print("N03D_F3_SOURCE_STATIC_CONTACT_FEASIBILITY",json.dumps({"scene":result["source_scene_sha256"],
  "actors":[{"actor":p["actor"],"sides":{k:{"window_count":q["window_count"],
    "max_mincircle_radius_m":q["source_maximax_radius_m"],
    "candidate_windows_within_40mm":sum(int(v["hypothetical_40mm_xy_correction_feasible"]) for v in q["windows"]),
    "short_window_sensitivity":[{"duration_seconds":w["duration_seconds"],
      "windows":w["windows"],"within_40mm":w["windows_at_most_40mm"],
      "min_radius_m":w["minimum_mincircle_radius_m"]} for w in q["duration_sensitivity"]]}
    for k,q in p["sides"].items()}} for p in reports],"actual_stance_accepted":False},sort_keys=True),flush=True)
if __name__=="__main__":main()
