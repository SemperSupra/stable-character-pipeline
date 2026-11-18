"""R088 source-authenticated measured 100STYLE BVH numerical preflight.
Third-party shortened BVH files remain ephemeral; observations are not ground truth
contacts nor a retargeted MPFB animation. Stdlib only, fail closed.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

SOURCE_COMMIT = "10938b4881b55c5801faded89e427407ddf14bce"
SOURCES = {
 "Neutral_FW.bvh": "a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61",
 "Neutral_TR1.bvh": "1b7af92a4df47d4f5e12db32bac90a968a03e0b9",
 "Old_FW.bvh": "a3b13a437de7d2151f3c9743d51b5ccfe332b3bd",
}
REQUIRED = {"Hips","LeftHip","RightHip","LeftKnee","RightKnee",
            "LeftAnkle","RightAnkle","LeftToe","RightToe"}

def reject(reason):
 raise ValueError(reason)

def sha256(data):
 return hashlib.sha256(data).hexdigest()

def git_blob_sha(data):
 return hashlib.sha1(("blob "+str(len(data))+"\x00").encode()+data).hexdigest()

def parse_bvh(blob, *, strict=True):
 if len(blob)>2_000_000 or len(blob)<40:reject("BOUNDED_SOURCE_SIZE")
 try: text=blob.decode("ascii")
 except UnicodeError:reject("BVH_NOT_ASCII")
 lines=[line.strip() for line in text.splitlines() if line.strip()]
 if not lines or lines[0]!="HIERARCHY" or lines.count("MOTION")!=1:reject("BVH_BOUNDARY")
 motion=lines.index("MOTION")
 nodes=[]; stack=[]; pending=None; channels=0
 for ln in lines[1:motion]:
  toks=ln.split()
  if toks[0] in ("ROOT","JOINT") or ln=="End Site":
   if pending is not None:reject("MISSING_OPEN_BRACE")
   if toks[0]=="ROOT" and (nodes or stack):reject("MULTIPLE_ROOT")
   if toks[0]=="JOINT" and not stack:reject("ORPHAN_JOINT")
   if ln=="End Site" and not stack:reject("ORPHAN_END_SITE")
   name= (stack[-1] and nodes[stack[-1]]["name"]+"_end") if ln=="End Site" else toks[1]
   if not isinstance(name,str) or not name:reject("EMPTY_BONE_NAME")
   if ln!="End Site" and any(n["name"]==name for n in nodes):reject("DUPLICATE_BONE")
   parent=stack[-1] if stack else None
   nodes.append({"name":name,"parent":parent,"offset":None,"channels":[],"start":channels,"end":ln=="End Site"})
   pending=len(nodes)-1
  elif ln=="{":
   if pending is None:reject("UNEXPECTED_BRACE")
   stack.append(pending);pending=None
  elif ln=="}":
   if not stack or pending is not None:reject("EXTRA_CLOSING_BRACE")
   stack.pop()
  elif toks[0]=="OFFSET":
   if not stack or nodes[stack[-1]]["offset"] is not None or len(toks)!=4:reject("INVALID_OFFSET")
   try: v=tuple(float(x) for x in toks[1:])
   except ValueError:reject("INVALID_OFFSET_FLOAT")
   if not all(math.isfinite(x) and abs(x)<10000 for x in v):reject("NONFINITE_OR_GIANT_OFFSET")
   nodes[stack[-1]]["offset"]=v
  elif toks[0]=="CHANNELS":
   if not stack or nodes[stack[-1]]["channels"] or nodes[stack[-1]]["end"]:reject("INVALID_CHANNEL_OWNER")
   try: count=int(toks[1])
   except (ValueError,IndexError):reject("BAD_CHANNEL_COUNT")
   types=toks[2:]
   allowed={"Xposition","Yposition","Zposition","Xrotation","Yrotation","Zrotation"}
   if len(types)!=count or len(set(types))!=count or not set(types)<=allowed or count not in (3,6):reject("INVALID_CHANNELS")
   nodes[stack[-1]]["channels"]=types
   nodes[stack[-1]]["start"]=channels
   channels+=count
  else:reject("UNKNOWN_BVH_TOKEN")
 if pending is not None or stack or not nodes or nodes[0]["name"]!="Hips":reject("UNBALANCED_HIERARCHY")
 if any(n["offset"] is None or (not n["end"] and not n["channels"]) for n in nodes):reject("INCOMPLETE_JOINT")
 if motion+3>len(lines):reject("MISSING_MOTION_HEADER")
 a=re.fullmatch(r"Frames:\s*(\d+)",lines[motion+1])
 b=re.fullmatch(r"Frame Time:\s*([0-9.eE+-]+)",lines[motion+2])
 if not a or not b:reject("BAD_FRAME_HEADER")
 count=int(a.group(1));dt=float(b.group(1))
 if not 2<=count<=25000 or not math.isfinite(dt) or not 0<dt<1:reject("BAD_FRAME_CLOCK")
 if abs(dt-1/60)>2e-5:reject("NOT_60_FPS_SOURCE")
 samplelines=lines[motion+3:]
 if len(samplelines)!=count:reject("FRAME_COUNT_MISMATCH")
 if channels>300:reject("TOO_MANY_CHANNELS")
 frames=[]
 for ln in samplelines:
  words=ln.split()
  if len(words)!=channels:reject("CHANNEL_VALUE_COUNT")
  try: frame=tuple(float(x) for x in words)
  except ValueError:reject("NONNUMERIC_CHANNEL")
  if not all(math.isfinite(x) and abs(x)<1e7 for x in frame):reject("NONFINITE_OR_GIANT_CHANNEL")
  frames.append(frame)
 names={n["name"] for n in nodes if not n["end"]}
 if strict and (not REQUIRED<=names or not 20<=len(names)<=35):reject("SKELETON_NOT_100STYLE")
 if nodes[0]["channels"]!=["Xposition","Yposition","Zposition","Yrotation","Xrotation","Zrotation"]:reject("ROOT_CHANNEL_CONVENTION")
 return {"nodes":nodes,"frames":frames,"frame_time":dt,"count":count,"channels":channels,
         "joints":len(names),"names":sorted(names)}

I=((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
def matmul(a,b):
 return tuple(tuple(sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)) for i in range(3))
def rotate(a,v):
 return tuple(sum(a[i][k]*v[k] for k in range(3)) for i in range(3))
def plus(a,b):return tuple(x+y for x,y in zip(a,b))
def axis_matrix(ax,deg):
 t=math.radians(deg);c=math.cos(t);s=math.sin(t)
 if ax=="X":return ((1,0,0),(0,c,-s),(0,s,c))
 if ax=="Y":return ((c,0,s),(0,1,0),(-s,0,c))
 return ((c,-s,0),(s,c,0),(0,0,1))

def fk(bvh,frame):
 f=bvh["frames"][frame]; poses=[];out={}
 for n in bvh["nodes"]:
  if n["parent"] is None:
   origin=(0.,0.,0.);parent_rotation=I
  else:
   origin, parent_rotation = poses[n["parent"]]
  translation=list(n["offset"]);local_rotation=I
  for ch,value in zip(n["channels"],f[n["start"]:n["start"]+len(n["channels"])]):
   if ch.endswith("position"):translation["XYZ".index(ch[0])]+=value
   else:local_rotation=matmul(local_rotation,axis_matrix(ch[0],value))
  pos=plus(origin,rotate(parent_rotation,translation))
  rot=matmul(parent_rotation,local_rotation)
  poses.append((pos,rot))
  if not n["end"]:out[n["name"]]=pos
 return out

def source_metrics(bvh):
 # All positions in centimeters, native X/Z are horizontal, Y vertical.
 # Foot-contact CANDIDATES only; ankles are not shoe-ground contacts.
 frames=bvh["count"];step=max(1,frames//600)
 indices=list(range(0,frames,step))
 root=[];feet={"LeftAnkle":[],"RightAnkle":[],"LeftToe":[],"RightToe":[]}
 for i in indices:
  pose=fk(bvh,i)
  root.append(pose["Hips"])
  for name in feet:feet[name].append(pose[name])
 def span(points,ax):return max(x[ax] for x in points)-min(x[ax] for x in points)
 candidates={}
 for name,coords in feet.items():
  floor=min(p[1] for p in coords)
  near=[i for i,p in enumerate(coords) if p[1]-floor<=1.5]
  velocities=[]
  for i in range(1,len(coords)):
   if (i in near) and (i-1 in near):
    a=coords[i-1];b=coords[i]
    velocities.append(math.hypot(b[0]-a[0],b[2]-a[2])*.01/(step*bvh["frame_time"]))
  candidates[name]={"minimum_world_y_cm":round(floor,5),
   "height_range_cm":round(span(coords,1),5),
   "near_minimum_sample_count":len(near),
   "near_minimum_horizontal_speed_max_mps":round(max(velocities),6) if velocities else None,
   "footwear_sole_contact_accepted":False}
 return {"frames":frames,"fps":round(1/bvh["frame_time"],7),
   "duration_seconds":round((frames-1)*bvh["frame_time"],5),
   "fk_sample_count":len(indices),"sample_stride":step,
   "root_horizontal_path_span_cm":round(math.hypot(span(root,0),span(root,2)),5),
   "source_world_y_up":True,"source_units":"centimeters",
   "inferred_world_ankle_toe_candidates":candidates,
   "ground_truth_contact_available":False,"planted_foot_contact_accepted":False}

def qualify(path, expected):
 p=Path(path)
 if p.name not in SOURCES or expected!=SOURCES[p.name] or not p.is_file():reject("SOURCE_NAME_OR_BLOB_PIN")
 data=p.read_bytes()
 if git_blob_sha(data)!=expected:reject("GIT_BLOB_CONTENT_DRIFT")
 bvh=parse_bvh(data)
 return {"schema":"scp.r088.real-100style-motion-fk-preflight.v1",
    "source_name":p.name,"source_git_commit":SOURCE_COMMIT,"source_git_blob_sha1":expected,
    "source_sha256":sha256(data),"source_bytes":len(data),
    "origin":"100STYLE Ian Mason et al Xsens motion 60fps, CC BY 4.0; shortened/rounded by tomcatmew simple_motion_matching",
    "source_changed_from_original":True,"license":"CC-BY-4.0 attribution required",
    "source_file_not_redistributed":True,"source_joint_count":bvh["joints"],
    "source_channel_count":bvh["channels"],"metrics":source_metrics(bvh),
    "status":"MEASURED_SOURCE_BVH_FK_NOT_RETARGETED",
    "mpfb_retarged_motion_accepted":False,"mvp_accepted":False,"release_authorized":False}

def main():
 a=argparse.ArgumentParser()
 a.add_argument("--source",required=True);a.add_argument("--sha1",required=True)
 a.add_argument("--out",required=True)
 args=a.parse_args()
 result=qualify(args.source,args.sha1)
 Path(args.out).write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("R088_SOURCE_MOTION",json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
