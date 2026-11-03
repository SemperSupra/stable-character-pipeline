#!/usr/bin/env python3
"""Independent *source-only* three-clock integration reviewer.
Never admit real human gait, original characters, biological ROM or CPE.
Rejects even internally consistent but unadmitted author-side mutations by
pinning exact bytes before controlled test-only fault injection.
"""
import argparse,copy,hashlib,json,math,pathlib,struct,sys
TRACE="1e56d63873b83dc33ea8f510932d1df0e09acfc66e9dae8880f2ae91658d5e86"
HIER="03a81c2a5ad6729f3022f4b1d4afbb94395c3a2b29b413ba601480c6995d463a"
BVH="ab3a0d712c9c4f21fba0cf0698568dd5f88f1b959cf8aae28173c6435153d760"
VMD="c24f86c00a9d2bae34e1b3928232aa2f6af976ae8169dfbcdbe8c33d6a235409"
ACTORS=["CobaltOriginal","MarigoldOriginal"]
class Reject(ValueError):pass
def digest(b):return hashlib.sha256(b).hexdigest()
def guard(ok,code):
    if not ok:raise Reject(code)
def inspect(trace,hier,fk,cross,vmd):
    guard(trace.get("schema")=="scp.shadow.original-two-actor.v1","SHADOW_SCHEMA")
    guard(hier.get("schema")=="scp.r009.public-hierarchical-skin.v1","HIER_SCHEMA")
    guard(trace.get("source_class")==hier.get("source_class")=="ORIGINAL_SELF_AUTHORED_SYNTHETIC","UNADMITTED_SOURCE")
    guard(trace.get("private_r009")==hier.get("private_R009")==cross.get("private_R009")=="HELD_NOT_ACCEPTED","FALSE_MVP_PROMOTION")
    guard(trace.get("measured_human")=="NOT_ADMITTED" and trace.get("authentic_identity")=="NOT_VERIFIED" and
          hier.get("physical_human_ROM")=="UNKNOWN" and hier.get("real_contact_force")=="UNKNOWN","FALSE_HUMAN_SCIENCE")
    guard(trace.get("fps")==hier.get("fps")==12 and trace.get("frame_count")==72 and
          len(trace.get("frames",[]))==len(hier.get("frames",[]))==72,"CLOCK_NOT_72_AT_12FPS")
    guard(trace.get("actor_ids")==ACTORS and hier.get("actor_ids")==["SyntheticLeft","SyntheticRight"],"ORIGINAL_ACTOR_ROLE_DRIFT")
    guard(trace.get("cameras",{}).get("front")!=trace.get("cameras",{}).get("oblique"),"CAMERA_ROLE_ALIAS")
    guard(trace["cameras"]["front"]["position"]==[0.,-7.2,3.4] and
          trace["cameras"]["oblique"]["position"]==[5.,-6.,3.7],"CAMERA_UNADMITTED_EXTRINSICS")
    guard(trace.get("geometry",{}).get("source_thigh_length_m")==.49 and
          trace["geometry"]["source_shin_length_m"]==.48,"SHADOW_GEOMETRY_INVALID")
    guard(hier.get("segment_lengths_m")==[.50,.48],"HIER_GEOMETRY_NOT_DECLARED")
    guard(hier.get("fixture_envelope_only")=={"hip_deg":[-35,35],"knee_deg":[0,125]},"NOT_SOURCE_AUTHORED_FIXTURE_ENVELOPE")
    weights=hier.get("skin_weights",{})
    for label in ("upper","knee","lower"):
        pair=weights.get(label)
        guard(isinstance(pair,list) and len(pair)==2 and all(isinstance(x,(int,float)) and math.isfinite(x) and 0<=x<=1 for x in pair) and
              abs(sum(pair)-1)<1e-9,"BAD_SKIN_DENOMINATOR:"+label)
    guard(0.1<weights["knee"][0]<0.9,"NO_DUAL_WEIGHTED_KNEE")
    for frame,(s,h) in enumerate(zip(trace["frames"],hier["frames"])):
        guard(s.get("frame")==h.get("frame")==frame and abs(s.get("time_seconds",-100)-frame/12)<2e-9,"SOURCE_CLOCK_FRAME:"+str(frame))
        guard(set(s.get("actors",{}))==set(ACTORS),"ACTOR_SOURCE_STATE:"+str(frame))
        guard(all(isinstance(h.get(k),(int,float)) and math.isfinite(h[k]) for k in ("hip_deg","knee_deg")),"NONFINITE_HIER_ANGLES")
        guard(-35<=h["hip_deg"]<=35 and 0<=h["knee_deg"]<=125,"FIXTURE_JOINT_ENVELOPE_ONLY")
        for actor in ACTORS:
            foot=s["actors"][actor]["feet"]
            guard(set(foot)=={"left","right"},"MISSING_FOOT_SIDE")
            for side in ("left","right"):
                state=foot[side]
                guard(type(state.get("contact")) is bool and len(state.get("ankle",[]))==3 and
                      all(isinstance(v,(int,float)) and math.isfinite(v) for v in state["ankle"]),"INVALID_AUTHORED_CONTACT")
    guard(fk.get("source_sha256")==BVH and fk.get("rights")=="ORIGINAL_SELF_AUTHORED_SYNTHETIC" and
          len(fk.get("frames",[]))==3,"BVH_SOURCE_NOT_ADMITTED")
    guard(cross.get("bvh_source_sha256")==BVH and cross.get("source_frames")==3 and
          cross.get("target_fps")==30 and cross.get("target_frame_pairs")==[[0,0],[2,1]] and
          cross.get("source_frame_1")=="DROPPED_30FPS_RESAMPLE","EXPLICIT_BVH_VMD_LOSS_MAP_MISSING")
    guard(cross.get("hierarchy_semantics")=="LOST_WORLD_TRANSLATION_ONLY_NOT_HUMAN_RETARGETING","FORGED_PHYSICAL_RETARGETING")
    guard(cross.get("synthetic_target_aliases")=={"Hips":"Hips","Knee":"Knee","Foot":"Foot"},"TARGET_BONE_ALIAS_FORGERY")
    guard(cross.get("vmd_sha256")==digest(vmd)==VMD,"VMD_BINARY_NOT_AUTHORED")
    guard(len(vmd)>=54 and vmd[:30].rstrip(b"\0")==b"Vocaloid Motion Data 0002" and
          struct.unpack_from("<I",vmd,50)[0]==6,"VMD_BINARY_RECORD_SHAPE")
    return {"schema":"scp.r009.independent-three-clock-source-inspection.v1",
       "status":"PASS_PUBLIC_ORIGINAL_SYNTHETIC_SOURCE_AND_LOSS_CONTRACT_ONLY",
       "source_roster":ACTORS,"shadow_fps":12,"hier_fps":12,
       "clean_camera_count":2,"debug_camera":"front_only",
       "shadow_bone_length_thigh_m":.49,"integrated_skin_bone_length_thigh_m":.50,
       "morphological_length_difference_m":.01,
       "bvh_clock_fps":60,"vmd_clock_fps":30,"dropped_bvh_frame":1,
       "72f_joint_clock_source":"SEPARATE_ORIGINAL_SYNTHETIC_HIP_KNEE",
       "vmd_used_as":"SPATIAL_CALIBRATION_ONLY_NOT_TEMPORAL_HUMAN_RETARGET",
       "root_gait_source":"SHADOW_AUTHOR_FIXTURE_NOT_HUMAN_CAPTURE",
       "contact_labels":"UNMEASURED",
       "source_sha256":{"shadow":TRACE,"hier":HIER,"bvh":BVH,"vmd":VMD},
       "human_ROM_JCS_contact":"UNKNOWN","protected_R009":"HELD_NOT_ACCEPTED",
       "merge":"HELD","CPE":"NOT_PROMOTED"}
def main():
    p=argparse.ArgumentParser()
    for n in ("shadow","hier","fk","crosswalk","vmd","out"):p.add_argument("--"+n,required=True)
    p.add_argument("--fault",choices=("baseline","camera_alias","false_human","clock_shift","bad_weights","false_MVP","short_trace","frame_gap","joint_range","bad_vmd","bad_fk","alias_bones","false_temporal","swap_actor","false_geometry"),default="baseline")
    a=p.parse_args()
    try:
        raw={n:pathlib.Path(getattr(a,n)).read_bytes() for n in ("shadow","hier","fk","crosswalk","vmd")}
        guard(digest(raw["shadow"])==TRACE and digest(raw["hier"])==HIER,"UNVERIFIED_AUTHOR_BYTES")
        guard(digest(raw["vmd"])==VMD,"UNVERIFIED_VMD_BYTES")
        s,h,f,c=map(lambda x:json.loads(raw[x]),("shadow","hier","fk","crosswalk"))
        if a.fault=="camera_alias":s["cameras"]["oblique"]=copy.deepcopy(s["cameras"]["front"])
        if a.fault=="false_human":h["physical_human_ROM"]="PASS"
        if a.fault=="clock_shift":h["fps"]=15
        if a.fault=="bad_weights":h["skin_weights"]["knee"]=[1.0,.4]
        if a.fault=="false_MVP":s["private_r009"]="ACCEPTED"
        if a.fault=="short_trace":s["frames"].pop()
        if a.fault=="frame_gap":s["frames"][26]["frame"]=25
        if a.fault=="joint_range":h["frames"][19]["knee_deg"]=151
        if a.fault=="bad_vmd":c["vmd_sha256"]="f"*64
        if a.fault=="bad_fk":f["source_sha256"]="f"*64
        if a.fault=="alias_bones":c["synthetic_target_aliases"]["Knee"]="L_Ankle"
        if a.fault=="false_temporal":c["hierarchy_semantics"]="HUMAN_TEMPORAL_RETARGET_PASS"
        if a.fault=="swap_actor":s["actor_ids"].reverse()
        if a.fault=="false_geometry":h["segment_lengths_m"][0]=.49
        report=inspect(s,h,f,c,raw["vmd"])
        guard(a.fault=="baseline","MUTANT_FALSE_ACCEPT:"+a.fault)
        with pathlib.Path(a.out).open("x") as out:json.dump(report,out,sort_keys=True,indent=2);out.write("\n")
        print(json.dumps(report,sort_keys=True))
    except (Reject,KeyError,IndexError,TypeError,ValueError,struct.error) as exc:
        print("THREE_CLOCK_SOURCE_REJECT:"+str(exc),file=sys.stderr)
        raise SystemExit(2)
if __name__=="__main__":main()
