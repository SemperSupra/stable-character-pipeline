"""Independent source-only paired native Blender XPBD vs Animation oracle.

No blender imports. Requires two actual 48f receipts produced from identical
original synthetic source and compares measured world/root-relative geometry.
Validation is engineering-only; no physics material calibration or release.
"""
import hashlib
import json
import math

SCHEMA="equine.blender52.paired_motion_quality.v1"
def vec(p):
    if type(p) not in (list,tuple) or len(p)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>100 for v in p):
        raise ValueError("bad 3D coordinate")
    return tuple(float(v) for v in p)
def norm(a,b):
    return math.sqrt(sum((a[i]-b[i])**2 for i in range(3)))
def validate_receipt(r,mode):
    if type(r)!=dict or r.get("schema")!="equine.blender52.dynamic.original_synthetic.v1":
        raise ValueError("unexpected receipt schema")
    if r.get("control_mode")!=mode or r.get("blender")!="5.2.3 LTS":
        raise ValueError("wrong source engine or control mode")
    if r.get("frame_count")!=48 or r.get("frames_requested")!=48 or type(r.get("samples"))!=list or len(r["samples"])!=48:
        raise ValueError("incomplete motion horizon")
    if not r.get("production_blender_4_5_15_untouched") or r.get("source_and_release_hold")!="KEEP" or r.get("visual_collision_quality")!="UNKNOWN" or r.get("errors"):
        raise ValueError("missing mandatory scientific hold or native error")
    if type(r.get("source_sha256"))!=str or len(r["source_sha256"])!=64 or any(c not in "0123456789abcdef" for c in r["source_sha256"]):
        raise ValueError("invalid source sha")
    if r.get("verdict")!=("EXPERIMENTAL_48F_MOTION_OBSERVED_NOT_SCIENTIFIC_ACCEPTANCE" if mode=="physics" else "CONTROL_RIGID_FOLLOW_CONFIRMED"):
        raise ValueError("wrong native verdict")
    if r.get("mode_control",{}).get("after")!=("Physics (Experimental)" if mode=="physics" else "Animation"):
        raise ValueError("mode not read back")
    samples=[]
    for i,row in enumerate(r["samples"]):
        if type(row)!=dict or type(row.get("frame")) is not int or row["frame"]!=i+1:
            raise ValueError("reordered or missing frame")
        if type(row.get("scalp_world_x_m")) not in (float,int) or not math.isfinite(row["scalp_world_x_m"]):
            raise ValueError("bad scalp source")
        triples=[]
        for label in ("root_world_m","tip_world_m","tip_minus_root_m"):
            values=row.get(label)
            if type(values)!=list or len(values)!=3:raise ValueError("missing 3 curves")
            triples.append([vec(v) for v in values])
        roots,tips,rel=triples
        for j in range(3):
            if norm(tuple(tips[j][k]-roots[j][k] for k in range(3)),rel[j])>1e-6:
                raise ValueError("forged relative-coordinate sample")
            if abs(roots[j][0]-row["scalp_world_x_m"]-(-.045,0.,.045)[j])>1e-5:
                raise ValueError("follicle has lost source root")
            if abs(roots[j][1])>1e-5:raise ValueError("unexpected source root y")
        samples.append({"root":roots,"tip":tips,"relative":rel,"scalp_x":float(row["scalp_world_x_m"])})
    return samples

def evaluate(physics,control):
    a=validate_receipt(physics,"physics")
    b=validate_receipt(control,"animation")
    if physics["source_sha256"]!=control["source_sha256"]:
        raise ValueError("different experiment source code")
    if any(abs(x["scalp_x"]-y["scalp_x"])>1e-6 for x,y in zip(a,b)):
        raise ValueError("different source motion timeline")
    if not max(abs(row["scalp_x"]) for row in a)>.10 or abs(a[-1]["scalp_x"])>.0001:
        raise ValueError("source control not excited and returned")
    span=max(norm(row["relative"][j],a[0]["relative"][j]) for row in a for j in range(3))
    control_span=max(norm(row["relative"][j],b[0]["relative"][j]) for row in b for j in range(3))
    max_pair_delta=max(norm(row["relative"][j],ref["relative"][j]) for row,ref in zip(a,b) for j in range(3))
    physics_v=max(norm(a[i]["relative"][j],a[i-1]["relative"][j])*24 for i in range(1,48) for j in range(3))
    control_v=max(norm(b[i]["relative"][j],b[i-1]["relative"][j])*24 for i in range(1,48) for j in range(3))
    strain=max(abs(math.sqrt(sum(x*x for x in row["relative"][j]))-.3)/.3 for row in a for j in range(3))
    final_lag=max(norm(a[-1]["relative"][j],a[0]["relative"][j]) for j in range(3))
    if not .01<span<.75 or control_span>.0001 or max_pair_delta<.01:
        raise ValueError("physics motion not independently distinguished from rigid-follow")
    if not 0<physics_v<8 or control_v>.0001:
        raise ValueError("nonphysical discontinuity or negative-control motion")
    if strain>.15:
        raise ValueError("excessive rod strain in uncontrolled original synthetic scenario")
    if not math.isfinite(final_lag):
        raise ValueError("invalid final lag")
    blob=json.dumps({"physics":a,"control":b},sort_keys=True,separators=(",",":")).encode()
    return {"schema":SCHEMA,"source_sha256":physics["source_sha256"],
        "measured_samples":48,"guides":3,
        "physics_tip_span_m":round(span,7),
        "animation_control_span_m":round(control_span,7),
        "max_paired_relative_tip_difference_m":round(max_pair_delta,7),
        "physics_max_tip_velocity_m_s":round(physics_v,7),
        "control_max_tip_velocity_m_s":round(control_v,7),
        "max_physics_tip_to_root_strain_fraction":round(strain,7),
        "final_frame_lag_after_surface_returns_m":round(final_lag,7),
        "observations_sha256":hashlib.sha256(blob).hexdigest(),
        "verdict":"PAIRED_NATIVE_SECONDARY_MOTION_ENGINEERING_OBSERVED",
        "science_and_visual":"UNKNOWN","physical_material_calibrated":False,
        "production_upgrade_approved":False,"merge_release_CPE":False}

def main():
    import pathlib,sys
    if len(sys.argv)!=4:raise SystemExit("usage: hair52_motion_quality.py physics.json animation.json receipt.json")
    raw=[json.loads(pathlib.Path(p).read_text()) for p in sys.argv[1:3]]
    result=evaluate(*raw)
    dest=pathlib.Path(sys.argv[3])
    if dest.exists():raise ValueError("will not overwrite existing quality receipt")
    dest.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("NATIVE_5_2_PAIRED_MOTION_SOURCE_ONLY",result)
if __name__=="__main__":main()
