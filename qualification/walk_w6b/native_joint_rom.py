"""W6B: native evaluated 24-frame source-driven knee joint geometry witness.

All angles are a MATHEMATICAL three-point surrogate in a world basis,
not biological ISB joint-coordinate angles or species-specific safe ROM.
"""
import argparse,hashlib,json,math
from pathlib import Path
import bpy
from mathutils import Vector

ACTORS=("CobaltOriginal","MarigoldOriginal")
LEGS=("Left","Right")
RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
def dist(a,b):return math.dist(a,b)
def knee_surrogate(h,k,a):
    u=Vector(h)-Vector(k);v=Vector(a)-Vector(k)
    if u.length<.01 or v.length<.01:raise ValueError("DEGENERATE_JOINT_GEOMETRY")
    c=max(-1.,min(1.,float(u.normalized().dot(v.normalized()))))
    return float(math.pi-math.acos(c))
def verify(source,observations):
    if source.get("schema")!="scp.walk_c4_original_ground_feasibility.v1" or source.get("rights")!=RIGHTS:
        raise ValueError("SOURCE_NOT_ADMITTED")
    if len(observations)!=24 or len(source.get("actors",[]))!=2:
        raise ValueError("FRAME_OR_ACTOR_COVERAGE")
    top_err=0.; stats={}
    for actor in source["actors"]:
        stats[actor["id"]]={}
        for leg in LEGS:stats[actor["id"]][leg]=[]
    for t,frame in enumerate(observations):
        if frame.get("tick")!=t or len(frame.get("actors",[]))!=2:
            raise ValueError("NONMONOTONIC_SOURCE_CLOCK")
        for idx,obs_actor in enumerate(frame["actors"]):
            src_actor=source["actors"][idx]
            if obs_actor["name"]!=src_actor["id"] or len(obs_actor.get("legs",[]))!=2:
                raise ValueError("ACTOR_OR_JOINT_SET_MISMATCH")
            for li,leg in enumerate(LEGS):
                entry=obs_actor["legs"][li];s=src_actor["frames"][t]["legs"][li]
                if entry["id"]!=leg or s["id"]!=leg:
                    raise ValueError("LEG_HOMOLOGY_OR_SOURCE_ORDER")
                for name in ("hip","knee","ankle"):
                    o=entry.get(name)
                    if not isinstance(o,list) or len(o)!=3 or any(type(q) not in (int,float) or not math.isfinite(q) for q in o):
                        raise ValueError("NONFINITE_OR_UNOBSERVED_JOINT")
                    err=dist(o,s[name]);top_err=max(err,top_err)
                    if err>0.001:raise ValueError("EVALUATED_NATIVE_SOURCE_JOINT_MISMATCH")
                knee=knee_surrogate(entry["hip"],entry["knee"],entry["ankle"])
                if abs(knee-entry["knee_surrogate_rad"])>1e-6:
                    raise ValueError("SURROGATE_ANGLE_MATH_MISMATCH")
                if not (0<=knee<=math.pi):
                    raise ValueError("UNBOUNDED_SURROGATE_ANGLE")
                stats[obs_actor["name"]][leg].append(knee)
    rates={}
    for actor,legs in stats.items():
        rates[actor]={}
        for leg,angles in legs.items():
            speed=[(angles[i]-angles[i-1])*12 for i in range(1,24)]
            acc=[(speed[i]-speed[i-1])*12 for i in range(1,len(speed))]
            jerk=[(acc[i]-acc[i-1])*12 for i in range(1,len(acc))]
            rates[actor][leg]={"observed_knee_bend_rad_min":min(angles),
                              "observed_knee_bend_rad_max":max(angles),
                              "observed_max_abs_velocity_rad_s":max(map(abs,speed)),
                              "observed_max_abs_acceleration_rad_s2":max(map(abs,acc)),
                              "observed_max_abs_jerk_rad_s3":max(map(abs,jerk)),
                              "real_physiological_limit":"UNKNOWN_UNQUALIFIED"}
    return {"max_native_source_joint_error":top_err,"mathematical_knee_rates":rates}

def run(folder):
    folder=Path(folder)
    src_raw=(folder/"source.json").read_bytes()
    source=json.loads(src_raw)
    receipt=json.loads((folder/"source_motion_receipt.json").read_text())
    blend=folder/"original_source_grounded_24frame_native.blend"
    if receipt.get("schema")!="scp.walk_w5d_native_grounded.v1" or receipt.get("source_sha256")!=hashlib.sha256(src_raw).hexdigest() or receipt.get("rights")!=RIGHTS:
        raise ValueError("FIRST_SOURCE_RECEIPT_MISMATCH")
    if hashlib.sha256(blend.read_bytes()).hexdigest()!=receipt.get("blend_sha256"):
        raise ValueError("NATIVE_BLEND_ORIGINAL_SHA_MISMATCH")
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    scene=bpy.context.scene
    observations=[]
    for tick in range(24):
        scene.frame_set(tick)
        frame={"tick":tick,"actors":[]}
        for actor in ACTORS:
            rig=bpy.data.objects.get(actor+"_Skeleton")
            if rig is None or rig.type!="ARMATURE" or len(rig.pose.bones)!=6:
                raise ValueError("ACTOR_RIG_MISSING_OR_REWRITTEN")
            a={"name":actor,"legs":[]}
            for leg in LEGS:
                upper=rig.pose.bones[leg+"Upper"];lower=rig.pose.bones[leg+"Lower"]
                h=list(map(float,rig.matrix_world@upper.head))
                k=list(map(float,rig.matrix_world@upper.tail))
                d=list(map(float,rig.matrix_world@lower.tail))
                # Assert continuity at bone joint, not only source-target agreement.
                if dist(k,list(map(float,rig.matrix_world@lower.head)))>0.001:
                    raise ValueError("NATIVE_KNEE_BONE_CONNECTIVITY")
                a["legs"].append({"id":leg,"hip":h,"knee":k,"ankle":d,
                                  "knee_surrogate_rad":knee_surrogate(h,k,d)})
            frame["actors"].append(a)
        observations.append(frame)
    result=verify(source,observations)
    # Deliberately corrupt one observed knee 10 cm; provenance must reject.
    malformed=json.loads(json.dumps(observations))
    malformed[10]["actors"][0]["legs"][0]["knee"][2]+=.1
    try:verify(source,malformed)
    except ValueError as err:
        if str(err)!="EVALUATED_NATIVE_SOURCE_JOINT_MISMATCH":raise
    else:raise ValueError("HOSTILE_WRONG_NATIVE_KNEE_PASSED")
    output={"schema":"scp.walk_w6b_joint_surrogate_observation.v1",
            "status":"PASS_SOURCE_KINEMATIC_MATCH_ONLY",
            "profile":source["profile"],"rights":RIGHTS,
            "original_blend_sha256":receipt["blend_sha256"],
            "original_source_sha256":receipt["source_sha256"],
            "frames_observed":24,"sample_rate_hz":12,
            "hostile_wrong_observed_knee":"REJECTED",
            "comparison":result,
            "human_anatomical_joint_coordinate":"UNKNOWN_NO_JCS",
            "animal_joint_ranges":"UNKNOWN_NO_TAXON",
            "hard_physical_feasibility":"UNKNOWN_NOT_PROVEN",
            "real_skin_visual":"NOT_MEASURED"}
    (folder/"native_joint_24frame_observed.json").write_text(json.dumps(observations,sort_keys=True,indent=2)+"\n")
    (folder/"native_joint_24frame_rom_receipt.json").write_text(json.dumps(output,sort_keys=True,indent=2)+"\n")
    print("W6B_NATIVE_24F_JOINT_SURROGATE",json.dumps(output,sort_keys=True))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--folder",required=True)
    run(p.parse_args().folder)
