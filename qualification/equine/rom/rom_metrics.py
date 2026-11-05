"""Independent equine ROM engineering falsifier (not a veterinary normal-range table).

Angle is 0 degrees for collinear proximal->joint->distal segments.
Bounded *engineering hypothesis* limits are conservative test thresholds, NOT
peer-reviewed biological norms. Front upper/lower junction is called
"carpus_candidate"; hind is "hock_candidate". A native hind stifle is MISSING
in the 26-joint source and is a mandatory anatomical failure.
"""
import math
from statistics import mean

LIMITS={
    "front_carpus_candidate": {"max_flexion_deg":115.0,"min_excursion_deg":3.0,"max_step_deg":24.0,"max_lateral_offset_m":.055},
    "hind_hock_candidate": {"max_flexion_deg":130.0,"min_excursion_deg":3.0,"max_step_deg":24.0,"max_lateral_offset_m":.055}
}
FEET=("front_L","front_R","hind_L","hind_R")
ANATOMY_MISSING=("hind_L_stifle","hind_R_stifle")

def evaluate_triplet(a, j, b):
    if not all(len(v)==3 and all(math.isfinite(float(q)) for q in v) for v in (a,j,b)):
        raise ValueError("invalid finite 3d joint positions")
    v=(j[0]-a[0],j[1]-a[1],j[2]-a[2])
    w=(b[0]-j[0],b[1]-j[1],b[2]-j[2])
    nv=math.sqrt(sum(x*x for x in v));nw=math.sqrt(sum(x*x for x in w))
    if nv<1e-5 or nw<1e-5:
        raise ValueError("zero-length limb segment")
    cosine=max(-1.0,min(1.0,sum(p*q for p,q in zip(v,w))/(nv*nw)))
    flex=math.degrees(math.acos(cosine))
    # Sagittal plane is XZ; uncontrolled side motion should be small.
    lateral=abs(j[1]-(a[1]+b[1])*.5)
    cross_y=v[2]*w[0]-v[0]*w[2]
    return {"flexion_deg":flex,"lateral_offset_m":lateral,
            "sagittal_bend_sign":1 if cross_y>1e-8 else (-1 if cross_y < -1e-8 else 0),
            "segment_lengths_m":[nv,nw]}

def evaluate(trajectories, source_bones):
    if set(trajectories)!=set(FEET):
        raise ValueError("four exact source limb chains required")
    issues=[]
    joint_reports={}
    for foot in FEET:
        arr=trajectories[foot]
        if len(arr)!=48 or [x["frame"] for x in arr]!=list(range(1,49)):
            raise ValueError("requires 48 contiguous observed frames")
        key=("front_carpus_candidate" if foot.startswith("front") else "hind_hock_candidate")
        limit=LIMITS[key]
        measurements=[evaluate_triplet(a["proximal"],a["joint"],a["distal"]) for a in arr]
        flex=[x["flexion_deg"] for x in measurements]
        lat=[x["lateral_offset_m"] for x in measurements]
        steps=[abs(flex[i+1]-flex[i]) for i in range(len(flex)-1)]
        bending_signs=[x["sagittal_bend_sign"] for x in measurements if x["flexion_deg"]>2 and x["sagittal_bend_sign"]!=0]
        sign_flips=sum(bending_signs[k]!=bending_signs[k-1] for k in range(1,len(bending_signs)))
        max_limb_length_delta=max(abs(x["segment_lengths_m"][k]-measurements[0]["segment_lengths_m"][k]) for x in measurements for k in (0,1))
        report={"name":key,"frames":48,
            "min_flexion_deg":round(min(flex),4),"max_flexion_deg":round(max(flex),4),
            "excursion_deg":round(max(flex)-min(flex),4),
            "max_step_deg":round(max(steps),4),"max_lateral_offset_m":round(max(lat),5),
            "sagittal_bend_sign_changes":sign_flips,
            "max_segment_length_delta_m":round(max_limb_length_delta,5),
            "first_four_frames":[{"frame":i+1,"flexion_deg":round(flex[i],3)} for i in range(4)],
            "engineering_limits":limit}
        joint_reports[foot]=report
        for violated,reason in [
            (max(flex)>limit["max_flexion_deg"],"overflexion"),
            (max(flex)-min(flex)<limit["min_excursion_deg"],"immobile_knee_or_hock"),
            (max(steps)>limit["max_step_deg"],"one_frame_joint_snap"),
            (max(lat)>limit["max_lateral_offset_m"],"transverse_plane_deviation"),
            (max_limb_length_delta>.02,"segment_length_not_invariant"),
            (sign_flips>2,"reversal_of_flexion_plane")
        ]:
            if violated:issues.append(f"{foot}:{reason}")
    for required in ANATOMY_MISSING:
        if required not in source_bones:
            issues.append("ANATOMICAL_MISSING_REQUIRED_JOINT:"+required)
    return {"schema":"equine.rom.science.v1","source":"actual_BlendGLB_evaluated_pose_world_joints",
            "coordinate_system":"object+world X forward, Z up; 0 degree straight vectors",
            "limit_basis":"CONSERVATIVE_PROVISIONAL_ENGINEERING_GUARDRAILS_NOT_CLINICAL_NORMAL_RANGES",
            "observed_frames":48,"joint_reports":joint_reports,"failure_codes":issues,
            "scientific_verdict":"JOINT_KINEMATICS_OR_ANATOMY_FAIL" if issues else "GUARDRAIL_NO_FAILURE_BIOLOGICAL_UNKNOWN",
            "behavioral_truth":"UNKNOWN",
            "limitations":"No force plates; missing scapular/carpal exact JCS; fetlock/pastern roll and scapular movement unqualified"}

