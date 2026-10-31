"""W8 synthetic actual Blender armature 24-tick six-bone source/ROM observation.

Source geometry is known but NOT source-qualified human biological JCS or force.
"""
import argparse, hashlib, json, math
from pathlib import Path
import bpy

ACTORS=("CobaltOriginal","MarigoldOriginal")
LEGS=("Left","Right")
RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"

def run(folder):
    folder=Path(folder)
    raw=(folder/"source.json").read_bytes()
    source=json.loads(raw)
    orig=json.loads((folder/"source_motion_receipt.json").read_text())
    sha=hashlib.sha256(raw).hexdigest()
    if source.get("schema")!="scp.walk_w7a_original_approach.v1" or source.get("rights")!=RIGHTS:
        raise ValueError("W8_SOURCE_UNADMITTED")
    if orig.get("source_sha256")!=sha or orig.get("frame_count")!=24 or orig.get("rights")!=RIGHTS:
        raise ValueError("W8_SOURCE_NATIVE_RECEIPT_SHA")
    blend=folder/"original_source_grounded_24frame_native.blend"
    blendsha=hashlib.sha256(blend.read_bytes()).hexdigest()
    if orig.get("blend_sha256")!=blendsha:
        raise ValueError("W8_NATIVE_BLEND_SHA_MISMATCH")
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    scene=bpy.context.scene
    observations=[]
    for tick in range(24):
        scene.frame_set(tick)
        o={"tick":tick,"actors":[]}
        for ai,name in enumerate(ACTORS):
            rig=bpy.data.objects.get(name+"_Skeleton")
            if not rig or rig.type!="ARMATURE" or len(rig.pose.bones)!=6:
                raise ValueError("W8_MISSING_ACTUAL_SIX_BONES")
            observed={"id":name,"bones":6,"legs":[]}
            for li,leg in enumerate(LEGS):
                s=source["actors"][ai]["frames"][tick]["legs"][li]
                upper=rig.pose.bones[leg+"Upper"]
                lower=rig.pose.bones[leg+"Lower"]
                foot=rig.pose.bones[leg+"Foot"]
                point=lambda v: [float(x) for x in rig.matrix_world@v]
                h=point(upper.head);k=point(upper.tail);a=point(lower.tail)
                lower_head=point(lower.head)
                foot_head=point(foot.head);foot_tail=point(foot.tail)
                if math.dist(k,lower_head)>.001:
                    raise ValueError("W8_NATIVE_KNEE_CHAIN_DISCONTINUITY")
                for label,now in (("hip",h),("knee",k),("ankle",a)):
                    if math.dist(now,s[label])>.001:
                        raise ValueError("W8_NATIVE_SOURCE_JOINT_MISMATCH_"+label)
                observed["legs"].append({
                    "id":leg,"hip":h,"knee":k,"ankle":a,
                    "foot_head":foot_head,"foot_tail":foot_tail,
                    "leg_bone_count":3})
            o["actors"].append(observed)
        observations.append(o)
    payload={"schema":"scp.walk_w8_native_sixbone_joint_observation.v1",
        "rights":RIGHTS,"source_sha256":sha,"blend_sha256":blendsha,
        "profile":source["profile"],"fps":12,"observations":observations,
        "native_evaluation":"ACTUAL_BLENDER_EVALUATED_ARMATURE_NOT_BIOLOGICAL"}
    (folder/"native_sixbone_joint_24frame.json").write_text(
        json.dumps(payload,sort_keys=True,indent=2)+"\n")
    print("W8_NATIVE_SIXBONE_24FRAME_SOURCE_OBSERVED",sha,blendsha)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("folder")
    run(p.parse_args().folder)
