"""Source-only exact Git pinned 100STYLE 360-frame 60 Hz original FK and candidate contacts."""
import argparse,hashlib,json,statistics,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent.parent/"r088-motion-real"))
from bvh_preflight import parse_bvh,git_blob_sha,fk,SOURCES,SOURCE_COMMIT
sys.path.insert(0,str(Path(__file__).parent))
from source_contact import summarize
def fail(s):raise ValueError(s)
def main():
 p=argparse.ArgumentParser()
 for arg in ("source","sha1","out"):p.add_argument("--"+arg,required=True)
 a=p.parse_args()
 src=Path(a.source);raw=src.read_bytes()
 if src.name not in SOURCES or a.sha1!=SOURCES[src.name] or git_blob_sha(raw)!=a.sha1:fail("FORGED_SOURCE_MOTION")
 bvh=parse_bvh(raw)
 if bvh["count"]!=2400:fail("EXPECTED_PINNED_REAL_2400_FRAME_SOURCE")
 idx=range(120,480)
 dt=bvh["frame_time"]
 coords={name:[] for name in ("Hips","LeftAnkle","LeftToe","RightAnkle","RightToe")}
 for i in idx:
  joints=fk(bvh,i)
  for name in coords:
   coords[name].append(tuple(float(x)*.01 for x in joints[name]))
 toes={name:summarize(coords[name],dt) for name in coords if name!="Hips"}
 root=coords["Hips"]
 result={"schema":"scp.n03d-l.100style-pre-retarget-60hz-foot-contact.v1",
   "name":src.name,"license":"CC BY 4.0 source modified by tomcatmew/simple_motion_matching",
   "source_git_commit":SOURCE_COMMIT,"source_git_blob_sha1":a.sha1,
   "source_sha256":hashlib.sha256(raw).hexdigest(),
   "sample_frames":[120,479],"sample_fps":round(1/dt,6),
   "source_units":"centimeters in BVH; reported meters after 0.01 conversion",
   "source_axes":"X,Z horizontal; Y vertical (source pre-Blender)",
   "root_span_world_horizontal_m":round(((max(x[0] for x in root)-min(x[0] for x in root))**2+(max(x[2] for x in root)-min(x[2] for x in root))**2)**.5,6),
   "root_speed":summarize(root,dt),
   "ankle_toe":toes,
   "threshold_m":.02,"near_ground_speed_threshold_mps":.08,
   "ground_source_floor_is_global_minimum_joint_height":True,
   "true_planted_contact_accepted":False,"post_retarget_kinematics_accepted":False,
   "mvp_accepted":False,"release_authorized":False}
 Path(a.out).write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+chr(10))
 print("N03D_L_ACTUAL_60HZ_SOURCE_CONTACT",json.dumps({"style":src.name,
  "root_span_m":result["root_span_world_horizontal_m"],
  "toe_and_ankle":{k:{"near_pairs":v["near_minimum_adjacent_pairs"],
   "median_near_velocity_mps":v["near_ground_p50_world_speed_mps"],
   "slow_episodes":v["slow_episode_count"],"longest_episode_s":max((p["duration_s"] for p in v["slow_near_ground_episodes"]),default=0)} for k,v in toes.items()},
  "source_contact_proven":False},sort_keys=True),flush=True)
if __name__=="__main__":main()
