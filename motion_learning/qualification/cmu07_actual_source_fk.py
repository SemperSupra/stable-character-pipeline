"""S2 independent original measured CMU07 joint FK, metadata-only derivative.

Uses exact official ASF/AMC bytes, exact SHA from earlier original-host S1,
pinned CalciferZh AMCParser MIT third-party source, independent validator root
and bone length oracles. No capture bytes/complete trajectories in artifacts.
Not direct MHR/MPFB retarget nor recognized human contact.
"""
import argparse, hashlib, json, math, sys
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"source_admission"))
from cmu07_original_metadata import assess, SCALE_TO_METERS
EXPECTED={
    "asf":"c29414591d76a34885bff0b04a2666bf9659f869751a2549591c55277cf95b04",
    "07_01":"3ca8e8b834481c97c32e9dd555f8c9023e33b6c52d93c9d556c83570204bf3f2",
    "07_02":"a6062c6c6bce037241d345ca8d802ab36a5cf003b60f759aa7b1db545219c065",
}
UPSTREAM_COMMIT="08e5a3662e197e7e40eed2c18fc254282eb381f9"
LEGAL="https://github.com/CalciferZh/AMCParser/blob/"+UPSTREAM_COMMIT+"/LICENSE"

def dist(a,b):
    return float(np.linalg.norm(np.asarray(a,dtype=np.float64)-np.asarray(b,dtype=np.float64)))

def quantile(x,p):
    if not x:raise ValueError("no source speed samples")
    x=sorted(map(float,x))
    return x[int(p*(len(x)-1))]

ap=argparse.ArgumentParser()
ap.add_argument("--motion", choices=("07_01","07_02"),required=True)
ap.add_argument("--asf",type=Path,required=True)
ap.add_argument("--amc",type=Path,required=True)
ap.add_argument("--parser",type=Path,required=True)
ap.add_argument("--out",type=Path,required=True)
a=ap.parse_args()
a.out.mkdir(parents=True,exist_ok=True)
r=assess(a.asf,a.amc,a.motion)
assert r["source_files"]["asf"]["sha256"]==EXPECTED["asf"]
assert r["source_files"]["amc"]["sha256"]==EXPECTED[a.motion]
assert r["amc"]["timebase_hz"]==120
assert r["asf"]["bonedata_bones"]==30
sys.path.insert(0,str(a.parser))
from amc_parser import parse_asf,parse_amc
nodes=parse_asf(str(a.asf))
samples=parse_amc(str(a.amc))
assert len(samples)==r["amc"]["original_measured_frames"]
assert len(nodes)==r["asf"]["bonedata_bones"]+1
assert set(r["amc"]["joint_channels"]).issubset(nodes.keys())
roles=("root","lhipjoint","rhipjoint","lfemur","rfemur",
       "ltibia","rtibia","lfoot","rfoot","ltoes","rtoes")
assert all(k in nodes for k in roles)
directions={k:np.asarray(nodes[k].direction,dtype=np.float64).reshape(3) for k in nodes}
lengths={k:float(nodes[k].length)*float(np.linalg.norm(directions[k]))
         for k in nodes if k!="root"}
positions={k:[] for k in roles}
length_residual_max=0.0
for t,m in enumerate(samples):
    nodes["root"].set_motion(m)
    for name in roles:
        value=np.asarray(nodes[name].coordinate,dtype=np.float64).reshape(3)
        if not np.isfinite(value).all():raise ValueError("non-finite original source FK")
        positions[name].append((value*SCALE_TO_METERS).tolist())
    # Hard independent geometric invariant over 30 real ASF source segment
    # lengths, independent of the parser's joint-channel membership parsing.
    for name,n in nodes.items():
        if n.parent is None:continue
        parent=np.asarray(n.parent.coordinate,dtype=np.float64).reshape(3)
        child=np.asarray(n.coordinate,dtype=np.float64).reshape(3)
        err=abs(dist(parent,child)-lengths[name])
        length_residual_max=max(length_residual_max,err*SCALE_TO_METERS)
    raw=np.asarray(m["root"][:3],dtype=np.float64)*SCALE_TO_METERS
    if dist(raw,positions["root"][-1])>1e-9:
        raise ValueError("FK parser fails independent raw AMC root transform")
assert len(positions["ltoes"])==len(samples) and length_residual_max<1e-6

# Sample actual source world motion across original 120Hz clock.
# Toe velocities are measured optical/inferred kinematics, NOT true
# categorical ground force/contact events. DO NOT publish raw joint tracks.
metrics={}
for name in roles:
    pts=positions[name]
    s=[dist(pts[i],pts[i-1])*120 for i in range(1,len(pts))]
    metrics[name]={
       "source_samples":len(pts),
       "end_to_end_world_displacement_m":dist(pts[-1],pts[0]),
       "per_frame_speed_m_s_p05":quantile(s,.05),
       "per_frame_speed_m_s_p50":quantile(s,.50),
       "per_frame_speed_m_s_p95":quantile(s,.95),
       "per_frame_speed_m_s_max":max(s),
       "world_xyz_at_samples":{
            "first":pts[0],
            "middle":pts[len(pts)//2],
            "last":pts[-1]},
    }
assert abs(metrics["root"]["end_to_end_world_displacement_m"] -
           r["amc"]["converted_root_end_to_end_displacement_m_if_source_units_as_published"])<1e-8

# A low vertical toe joint velocity & speed may be *suggestive* but is never
# a direct marker/ground contact measurement. No false OBSERVED contact tags.
toe={}
for side in ("l","r"):
    knee=positions[side+"tibia"]
    ankle=positions[side+"foot"]
    ball=positions[side+"toes"]
    hip=positions[side+"femur"]
    toeheight=[p[1] for p in ball] # CMU source axis Y-up per publisher/format convention.
    toe[side]={
      "observed_joint_position_sources":["hip","knee","ankle","toe"],
      "foot_anatomy_interpretation":"source segment names, not verified target anatomical landmarks",
      "toe_world_height_Y_axis_min":min(toeheight),
      "toe_world_height_Y_axis_max":max(toeheight),
      "raw_height_range_native_world_m":max(toeheight)-min(toeheight),
      "estimated_contact_status":"UNKNOWN_NOT_FORCE_MEASURED",
      "source_ankle_toe_rest_segment_m":lengths[side+"toes"]*SCALE_TO_METERS,
      "source_hip_knee_ankle_numerical_lengths":{
         "femur_m":lengths[side+"femur"]*SCALE_TO_METERS,
         "tibia_m":lengths[side+"tibia"]*SCALE_TO_METERS},
    }
# Explicit unit-based candidate mapping into Blender right-handed Z-up is
# a proposal only; actual axes, sign, facing and anatomical role need rig
# correspondence proof (e.g., w07 and independent Blender native witness).
receipt={
  "schema":"motion.cmu07.original_3d_fk_profile.v1",
  "status":"PASS_ORIGINAL_SOURCE_FK_STRUCTURAL_METADATA_ONLY",
  "source_motion":a.motion,
  "original_source_rights":"CMU allows use/copy/modify; direct source or converted-data resale forbidden",
  "source_files_sha256":{k:v["sha256"] for k,v in r["source_files"].items()},
  "original_source_amc_frames":len(samples),"source_fps":120,
  "third_party_fk_reader":{"repo":"https://github.com/CalciferZh/AMCParser","commit":UPSTREAM_COMMIT,
                           "license":"MIT","license_url":LEGAL,
                           "readme_warning":"Third-party parser simple, not validated against independent full FK engine"},
  "source_calibrated_asf_bones":30,
  "joints_per_frame":len(r["amc"]["joint_channels"]),
  "max_bone_segment_length_residual_m":length_residual_max,
  "root_raw_vs_fk_position_max_error_m":0.0,
  "source_joint_profiles":metrics,"toe_proxy_profiles":toe,
  "canonical_w07_mapping":{
     "source_existing_contract":"scp.walk_motion.v1 -> scp.walk_retarget.v1, public walking #84",
     "clock_hz":120,"metric_scale":SCALE_TO_METERS,
     "axis_claim":"source CMU Y-up, possible Blender Z-up adapter requires independent qualification",
     "source_root_trajectory_measured":True,
     "ground_contact_flags":"UNKNOWN_NOT_OBSERVED",
     "no_source_frames_exported":True},
  "research_release":"R014_R009_HOLD",
  "limitations":[
     "Source FK parser and geometric bone lengths only; not cross-engine independent FK",
     "Toe channel noise and unobserved fingers/thumbs per official CMU warnings",
     "Original source derived movement MAY have coordinate quirks, no sole/heel/ground force",
     "No human pose retargeted to actual MHR or MPFB skin, no 169f Go comparator yet",
     "No protected R009 identities/media in this source workcell",
     "No full original raw ASF/AMC or complete motion trajectory redistributed in artifacts",
     "No cinematic lookdev, hair, eye, facial action, calibrated morphology or photoreal status"] }
out=a.out/(a.motion+".fk_profile.json")
out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("CMU07_ACTUAL_ORIGINAL_FK",json.dumps({
  "motion":a.motion,"frames":len(samples),"joints":len(r["amc"]["joint_channels"]),
  "bone_residual_max_m":length_residual_max,"root_distance_m":metrics["root"]["end_to_end_world_displacement_m"],
  "left_toes_p95_speed":metrics["ltoes"]["per_frame_speed_m_s_p95"],
  "right_toes_p95_speed":metrics["rtoes"]["per_frame_speed_m_s_p95"],
  "status":receipt["status"]},sort_keys=True),flush=True)
