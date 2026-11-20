"""Joint-root-foot 125ms window feasibility on source SHA-pinned genuine shoe trace."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from solver import SIDES,solve
def require(x,why):
 if not x:raise ValueError(why)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--trace",required=True);p.add_argument("--out",required=True)
 a=p.parse_args()
 b=Path(a.trace).read_bytes();t=json.loads(b)
 require(t.get("schema")=="scp.n03d-g.evaluated-foot-contact-observer.v1","TRACE_SCHEMA_DRIFT")
 require(t.get("source_class")=="ORIGINAL_FICTIONAL_CC0","PROTECTED_SOURCE")
 require(t.get("frame_rate_hz")==24 and t.get("sample_count_per_side")==143,"SOURCE_CLOCK_DRIFT")
 require(len(t.get("actors",[]))==2 and sorted(z["actor"] for z in t["actors"])==["AsterOriginal","JuniperOriginal"],"ACTOR_SET_WRONG")
 actors=[]
 for actor in t["actors"]:
  require(set(actor["sides"])==set(SIDES) and actor.get("native_bones")==163,"NATIVE_SOURCE_RIG_OR_SHOE_MISMATCH")
  sampled={}
  for s in SIDES:
   rows=actor["sides"][s]["samples"]
   require(len(rows)==143,"SAMPLE_COUNT_CHANGED")
   for i,row in enumerate(rows):
    require(abs(row["t_s"]-i/24.)<1e-7,"SAMPLE_TIME_REORDER")
   sampled[s]=[(r["xy_m"][0],r["xy_m"][1],r["z_m"]) for r in rows]
  windows=[]
  for start in (24,48,72,96):
   points={s:[list(x) for x in sampled[s][start:start+4]] for s in SIDES}
   modes=[solve(points,mode) for mode in ("root_only","foot_only","joint")]
   windows.append({"native_24hz_start_sample":start,"duration_s":.125,"modes":modes,
     "true_planted_window_detected":False,"source_joint_side_anatomy_verified":False})
  actors.append({"actor":actor["actor"],"windows":windows})
 out={"schema":"scp.n03d-v.actual-sole-joint-root-temporal-feasibility.v1",
 "trace_sha256":hashlib.sha256(b).hexdigest(),"source_scene_sha256":t["source_scene_sha256"],
 "original_character_rights":"ORIGINAL_FICTIONAL_CC0","clock_hz":24,
 "source_100style_sha256":t["source_100style_sha256"],
 "per_component_root_and_foot_movement_bound_m":.04,
 "actors":actors,"source_shoe_patch_proxy_not_persistent_material_vertices":True,
 "source_stance_segments_not_admitted":True,"root_and_foot_corrections_not_actuated":True,
 "independent_post_IK_native_observer_completed":False,
 "mvp_accepted":False,"release_authorized":False}
 Path(a.out).write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("N03D_V_REAL_JOINT_ROOT_FOOT_FEASIBILITY",json.dumps({"actors":[{"actor":x["actor"],"windows":[{"start":w["native_24hz_start_sample"],
  "mode_summaries":[{"mode":m["mode"],"objective_before":m["objective_initial"],"objective_after":m["objective_final"],
  "max_xy_residual_m":m["max_xy_stationary_proxy_residual_m"],
  "max_z_penetration_m":m["max_ground_proxy_penetration_m"],
  "max_z_hover_m":m["max_ground_proxy_hover_m"]}
   for m in w["modes"]]} for w in x["windows"]]} for x in actors],
  "native_actuation_accepted":False},sort_keys=True),flush=True)
if __name__=="__main__":main()
