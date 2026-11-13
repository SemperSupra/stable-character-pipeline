"""Generate an EPHEMERAL source CMU07 measured 3D walk target packet.

Original ASF/AMC capture and complete captured/donor-derived trajectories stay
in runner TEMP. Do not artifact/upload frames or original capture without
source-specific owner admission. Geometry-only research for R014 MHR.
"""
import argparse, hashlib, json, math, sys
from pathlib import Path
import numpy as np

EXPECTED={
 "asf":"c29414591d76a34885bff0b04a2666bf9659f869751a2549591c55277cf95b04",
 "07_01":"3ca8e8b834481c97c32e9dd555f8c9023e33b6c52d93c9d556c83570204bf3f2",
 "07_02":"a6062c6c6bce037241d345ca8d802ab36a5cf003b60f759aa7b1db545219c065",
}
METRE_FACTOR=(1/.45)*2.54/100
ap=argparse.ArgumentParser()
ap.add_argument("--asf",type=Path,required=True)
ap.add_argument("--amc",type=Path,required=True)
ap.add_argument("--motion",choices=("07_01","07_02"),required=True)
ap.add_argument("--parser",type=Path,required=True)
ap.add_argument("--out",type=Path,required=True)
a=ap.parse_args()
for path,key in ((a.asf,"asf"),(a.amc,a.motion)):
 assert hashlib.sha256(path.read_bytes()).hexdigest()==EXPECTED[key], "wrong source capture bytes"
sys.path.insert(0,str(a.parser))
from amc_parser import parse_asf,parse_amc
bones=parse_asf(str(a.asf));source=parse_amc(str(a.amc))
assert len(bones)==31 and len(source)=={"07_01":316,"07_02":329}[a.motion]
required={"root","lhipjoint","rhipjoint","lfemur","rfemur","ltibia","rtibia","lfoot","rfoot","ltoes","rtoes"}
assert required.issubset(bones)
kin=[]
for amc in source:
 bones["root"].set_motion(amc)
 q={key:(np.asarray(bones[key].coordinate,dtype=float).reshape(3)*METRE_FACTOR) for key in required}
 assert all(np.isfinite(p).all() for p in q.values())
 kin.append(q)

# Original source basis declared Y-up. Project source horizontal root
# into target Blender +X forward, source measured height Y -> +Z,
# original source X/Z horizontal lateral orientation resolved from
# root start/end, without inferring anatomy or a natural pelvis yaw.
r0=kin[0]["root"];rn=kin[-1]["root"]
xz=np.array([rn[0]-r0[0],rn[2]-r0[2]],dtype=float)
travel=float(np.linalg.norm(xz))
assert travel>2.0,"wrong/missing source walking root"
forward=xz/travel
lateral=np.array([-forward[1],forward[0]])
def map_displacement(v):
 d=np.asarray(v,dtype=float)
 out=np.array([np.dot(d[[0,2]],forward),np.dot(d[[0,2]],lateral),d[1]],dtype=float)
 assert np.isfinite(out).all()
 return out

# 120Hz original -> 24Hz exact integer stride of 5 samples: no fabricated
# interpolation, explicit source sample index. The source original physical
# root/foot trajectories remain ephemeral and no new provenance is invented.
indices=list(range(0,len(kin),5))
assert 60<=len(indices)<=67
selected=[kin[i] for i in indices]
base=selected[0]
# A real human's pelvis is the mean bilateral hip-joint WORLD position.
# The AMC global root is a coordinate-frame node, not automatically the
# anatomical pelvis origin. Track the actually reconstructed hip midpoint.
def hip_mid(sample):
 return .5*(sample["lhipjoint"]+sample["rhipjoint"])
base_hip_mid=hip_mid(base)
initial_ankle_relative_hipcenter={}
for side in ("l","r"):
 v=map_displacement(base[side+"tibia"]-base_hip_mid)
 initial_ankle_relative_hipcenter[side]=dict(zip(("x","y","z"),map(float,v)))
source_leg_lengths={}
source_first_hip_ankle_vertical_m={}
source_first_hip_ankle_horizontal_m={}
for side in ("l","r"):
 # ASF source node coordinates represent the END of named segments:
 # lhipjoint ends at hip, lfemur ends at knee, ltibia ends at ankle.
 # Prior wrong lfemur->ltibia->lfoot was knee->ankle->midfoot and
 # materially undercounted leg reach. Pin to source #469/#485.
 hip=base[side+"hipjoint"];knee=base[side+"femur"];ankle=base[side+"tibia"]
 source_leg_lengths[side]=float(np.linalg.norm(hip-knee)+np.linalg.norm(knee-ankle))
 source_first_hip_ankle_vertical_m[side]=float(abs(hip[1]-ankle[1]))
 source_first_hip_ankle_horizontal_m[side]=float(np.linalg.norm((hip-ankle)[[0,2]]))
assert all(.4<x<1.5 for x in source_leg_lengths.values())
frames=[]
for t,(i,j) in enumerate(zip(indices,selected),start=1):
 root=map_displacement(hip_mid(j)-base_hip_mid)
 legs={}
 for side,field in (("l","left_leg"),("r","right_leg")):
  # Measured ankle from end of tibia, NOT from foot segment end.
  foot=map_displacement(j[side+"tibia"]-base[side+"tibia"])
  ball=map_displacement(j[side+"toes"]-base[side+"toes"])
  legs[field]={"ankle":dict(zip(("x","y","z"),map(float,foot))),
               "ball":dict(zip(("x","y","z"),map(float,ball))),
               "contact":False,   # genuine ground contact not directly observed
               "contact_evidence":"UNKNOWN_NOT_FORCE_MEASURED"}
 frames.append({"frame":t,"original_source_sample_one_indexed":i+1,
    "source_time_seconds":i/120.0,
    "root":dict(zip(("x","y","z"),map(float,root))),
    "heading_radians":0.0,
    "phase":"CMU_MEASURED_KINEMATICS_NOT_CONTACT",
    **legs})
assert len(frames)==len(indices) and frames[0]["original_source_sample_one_indexed"]==1
assert all(frames[k]["source_time_seconds"]>frames[k-1]["source_time_seconds"] for k in range(1,len(frames)))
receipt={
 "schema":"r014.motion.cmu07_ephemeral_target_packet.v1",
 "status":"SOURCE_MEASURED_3D_KINEMATIC_TRAJECTORY_NO_CONTACT_LABELS",
 "motion":a.motion,"source_fps":120,"target_fps":24,
 "original_source_frames":len(kin),"sampled_source_frames":len(frames),
 "source_first_last_sample_index":[indices[0]+1,indices[-1]+1],
 "source_asf_sha256":EXPECTED["asf"],"source_amc_sha256":EXPECTED[a.motion],
 "original_raw_root_horizontal_travel_m":travel,
 "original_root_forward_horizontal_xz":forward.tolist(),
 "source_leg_numerical_m":source_leg_lengths,
 "source_first_hip_ankle_vertical_m":source_first_hip_ankle_vertical_m,
 "source_first_hip_ankle_horizontal_m":source_first_hip_ankle_horizontal_m,
 "source_leg_joint_role_chain":{"l":["lhipjoint","lfemur","ltibia"],"r":["rhipjoint","rfemur","rtibia"]},
 "source_initial_ankle_relative_bilateral_hipcentre":initial_ankle_relative_hipcenter,
 "measured_motion_root_reference":"source true bilateral hipjoint centroid, NOT original AMC reference-frame root",
 "source_measured_ankle_end_node":"ltibia/rtibia",
 "original_unit_scale_publisher_only":METRE_FACTOR,
 "orientation":"SOURCE_Y_UP_ROOT_TRAVEL_TO_BLENDER_X_FORWARD; YAW_UNOBSERVED",
 "source_rights":"CMU official no direct resale of original or converted capture data",
 "contact":"UNKNOWN_NOT_FORCE_MEASURED; no planted-foot claim",
 "full_motion_data_venue":"EPHEMERAL_RUNNER_TEMP_ONLY",
 "limitation":"Target frames are direct sampled original FK positions; not joint rotations or MHR retarget success"
}
a.out.mkdir(parents=True,exist_ok=True)
(a.out/"cmu07_ephemeral_frames.json").write_text(json.dumps(frames,separators=(",",":"))+"\n")
(a.out/"cmu07_ephemeral_source_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("CMU07_REAL_TARGETS_PREPARED_EPHEMERAL",json.dumps({
 "motion":a.motion,"frames":len(frames),"root_travel":travel,
 "source_lengths":source_leg_lengths,
 "true_hip_motion_world_m":float(np.linalg.norm(map_displacement(hip_mid(selected[-1])-base_hip_mid))),
 "initial_hip_ankle_vertical_m":source_first_hip_ankle_vertical_m,
 "initial_hip_ankle_horizontal_m":source_first_hip_ankle_horizontal_m,
 "contact":receipt["contact"]},sort_keys=True),flush=True)
