"""W16-B4 explicit versioned dual-leg rest/bind matrices and rational clock.

Source: exact B3 generated original synthetic typed stream; no private assets,
no measured clock and no native Blender import equivalence claim.
"""
import argparse,hashlib,json,math
from fractions import Fraction
from pathlib import Path
RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
SRC="scp.walk_dual_leg_motion.v3"
DST="scp.walk_dual_leg_rest_clock.v4"
ACTORS=("CobaltOriginal","MarigoldOriginal")
FRAME_IDS=(0,12,24,36,48,60,71)
def norm(v):return math.sqrt(sum(x*x for x in v))
def sub(a,b):return [a[i]-b[i] for i in range(3)]
def add(a,b):return [a[i]+b[i] for i in range(3)]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def rotate(q,v):
 t=[2*x for x in cross(q[:3],v)]
 c=cross(q[:3],t)
 return [v[i]+q[3]*t[i]+c[i] for i in range(3)]
def qmul(a,b):
 x,y,z,w=a;X,Y,Z,W=b
 return [w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,w*Z+x*Y-y*X+z*W,w*W-x*X-y*Y-z*Z]
def inv(a):return [-a[0],-a[1],-a[2],a[3]]
def matrix(t):
 return [1.,0.,0.,float(t[0]),0.,1.,0.,float(t[1]),0.,0.,1.,float(t[2]),0.,0.,0.,1.]
def valid(s):
 if s.get("Schema")!=SRC or s.get("Rights")!=RIGHTS or s.get("ClockOrigin")!="SYNTHETIC_ZERO_NO_MEASURED_CLOCK":
  raise ValueError("BAD_SOURCE_RIGHTS_CLOCK")
 if s.get("OriginSHA")!="e0a42b8d5dfe23334486ff195ac90fe6b7d3a199":raise ValueError("BAD_SOURCE_ORIGIN")
 if s.get("FPSNum")!=12 or s.get("FPSDen")!=1 or s.get("Basis")!="BLENDER_RH_Z_UP_SOURCE" or s.get("QuatOrder")!="GLTF_XYZW_COMPONENTS_Z_UP_FRAME":
  raise ValueError("SOURCE_CLOCK_BASIS")
 if s.get("Profile") not in ("forward","outward"):raise ValueError("PROFILE")
 if len(s.get("Actors",[]))!=2:raise ValueError("ACTOR_SET")
def build(source):
 s=json.loads(source,parse_constant=lambda x: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))
 valid(s)
 output=[];max_fk=0.
 for actor_index,a in enumerate(s["Actors"]):
  if a["ID"]!=ACTORS[actor_index] or a["Rest"]!=["LeftUpper","LeftLower:LeftUpper","RightUpper","RightLower:RightUpper"]:
   raise ValueError("REST_HIERARCHY")
  bones=[]
  for label,sign in (("Left",-1),("Right",1)):
   x=sign*.22
   for bone,par,head,tail in (
    (label+"Upper","",[x,0,1.4],[x,0,.8]),
    (label+"Lower",label+"Upper",[x,0,.8],[x,0,.2])):
    rest_bind=[float(z) for z in head]
    parent_offset=[0.,0.,0.] if not par else [0.,0.,-.6]
    bones.append({"id":bone,"parent":par,"rest_head":head,"rest_tail":tail,
     "world_rest_bind_rowmajor":matrix(head),"parent_local_rest_bind_rowmajor":matrix(parent_offset),
     "rest_local_quat_xyzw":[0.,0.,0.,1.]})
  frames=[]
  if len(a["Frames"])!=7:raise ValueError("FRAME_COVERAGE")
  for j,f in enumerate(a["Frames"]):
   if f["Frame"]!=FRAME_IDS[j] or f["TimeNum"]!=f["Frame"] or f["TimeDen"]!=12:raise ValueError("FRAME_CLOCK")
   if len(f["Legs"])!=2:raise ValueError("TWO_LEGS")
   pose=[]
   root=f["Root"]
   for leg_index,leg in enumerate(f["Legs"]):
    label,sign=(("Left",-1),("Right",1))[leg_index]
    if leg["ID"]!=label or leg["Contact"]!="unknown" or leg["Parent"]!=label+"Upper":
     raise ValueError("LEG_PARENT_OR_FALSE_CONTACT")
    upper,lower=leg["UpperWorld"],leg["LowerWorld"]
    for q in (upper,lower):
     if len(q)!=4 or any(not math.isfinite(x) for x in q) or abs(sum(x*x for x in q)-1)>1e-6:
      raise ValueError("QUAT_UNADMITTED")
    child_local=qmul(inv(upper),lower)
    hip=[root[0]+sign*.22,root[1],root[2]+1.4]
    observed_knee=add(hip,rotate(upper,[0,0,-.6]))
    observed_end=add(observed_knee,rotate(qmul(upper,child_local),[0,0,-.6]))
    err=max(norm(sub(observed_knee,leg["Knee"])),norm(sub(observed_end,leg["Ankle"])))
    max_fk=max(max_fk,err)
    if err>1e-8:raise ValueError("PARENT_RELATIVE_FK_SOURCE")
    pose.extend([
     {"bone":label+"Upper","local_quat_xyzw":upper},
     {"bone":label+"Lower","local_quat_xyzw":child_local}])
   frame_time=Fraction(f["TimeNum"],f["TimeDen"])
   sample_index=frame_time*48000
   if sample_index.denominator!=1:raise ValueError("PCM_SAMPLE_NOT_INTEGER")
   frames.append({"index":f["Frame"],"time_num":frame_time.numerator,
     "time_den":frame_time.denominator,"sample_index_48k":sample_index.numerator,
     "root_xyz_zup":root,"bone_local_quats":pose})
  output.append({"id":a["ID"],"rest_bones":bones,"frames":frames})
 r={"schema":DST,"rights":RIGHTS,"source_schema":SRC,"source_sha256":hashlib.sha256(source).hexdigest(),
  "origin_sha":"e0a42b8d5dfe23334486ff195ac90fe6b7d3a199",
  "basis":"BLENDER_RH_Z_UP_SOURCE","quat":"GLTF_XYZW_COMPONENTS_Z_UP_FRAME",
  "clock_scope":"SYNTHETIC_ZERO_UNCALIBRATED","fps":"12/1","pcm_rate":"48000/1",
  "profile":s["Profile"],"actors":output,
  "max_local_fk_source_unit":max_fk,
  "contact":"ALL_UNKNOWN_NO_SOLE_SOURCE",
  "status":"PASS_SOURCE_ONLY_TYPED_REST_AND_CLOCK"}
 return r
def main():
 p=argparse.ArgumentParser();p.add_argument("--source",required=True);p.add_argument("--out",required=True);a=p.parse_args()
 receipt=build(Path(a.source).read_bytes());Path(a.out).write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
 print("W16B4_SOURCE_REST_CLOCK_PASS",receipt["max_local_fk_source_unit"])
if __name__=="__main__":main()
