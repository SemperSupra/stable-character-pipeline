"""W7A: new ORIGINAL X-approach 24-frame source into native six-bone Blender.

This is an unreviewed source-gait feasibility rep, not physiological human
walking, full body, skin/texture acceptance, or owner private character.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"walk_w16c5a"))
import bpy
from mathutils import Vector, Quaternion
from native_sole import add_actor,ACTORS,LEGS,SOURCE

def animate(source,profile,out):
    if (source.get("schema")!="scp.walk_w7a_original_approach.v1" or
        source.get("rights")!=SOURCE or source.get("profile")!=profile or
        len(source.get("actors",[]))!=2 or source.get("fps_num")!=12 or source.get("root_x_travel_per_actor")!=.33):
        raise ValueError("C4_SOURCE_CONTRACT_OR_RIGHTS")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.frame_start=0;scene.frame_end=23;scene.render.fps=12
    assets=[]
    for i,(name,x) in enumerate(ACTORS):
        if source["actors"][i]["id"]!=name or len(source["actors"][i]["frames"])!=24:
            raise ValueError("C4_ACTOR_ID_OR_FRAME_COUNT")
        assets.append(add_actor(name,x))
    max_joint_error=0.0
    max_foot_error=0.0
    max_native_stance_slip=0.0
    min_native_sole=math.inf
    stance_count=swing_count=0
    prior_stance={}
    witness=[]
    for tick in range(24):
        scene.frame_set(tick)
        sample={"frame":tick,"actors":[]}
        for ai,(arm,obj,landmarks) in enumerate(assets):
            f=source["actors"][ai]["frames"][tick]
            if f["index"]!=tick or f["time_num"]!=tick or f["time_den"]!=12 or len(f["legs"])!=2:
                raise ValueError("C4_CLOCK_OR_LEG_COVERAGE")
            arm.location.y=f["root_y"]
            arm.location.x=f["root_x"]
            arm.keyframe_insert(data_path="location",frame=tick)
            actor_sample={"name":ACTORS[ai][0],"legs":[]}
            direction=1 if profile=="forward" else -1
            foot_world=Quaternion((1,0,0,0)) if direction>0 else Quaternion((0,0,1),math.pi)
            for li,(leg,sign) in enumerate(LEGS):
                s=f["legs"][li]
                if s["id"]!=leg or s["source_rights"]!=SOURCE:
                    raise ValueError("C4_LEG_ID_OR_RIGHTS")
                hip,knee,ankle=map(Vector,(s["hip"],s["knee"],s["ankle"]))
                base=Vector((0,0,-1))
                wu=base.rotation_difference((knee-hip).normalized())
                wl=base.rotation_difference((ankle-knee).normalized())
                bones=[arm.pose.bones[leg+part] for part in ("Upper","Lower","Foot")]
                ru=arm.data.bones[leg+"Upper"].matrix_local.to_quaternion()
                rl=arm.data.bones[leg+"Lower"].matrix_local.to_quaternion()
                rf=arm.data.bones[leg+"Foot"].matrix_local.to_quaternion()
                bones[0].rotation_quaternion=ru.inverted()@wu@ru
                bones[1].rotation_quaternion=rl.inverted()@wu.inverted()@wl@rl
                bones[2].rotation_quaternion=rf.inverted()@wl.inverted()@foot_world@rf
                for bone in bones:
                    bone.rotation_mode="QUATERNION"
                    bone.keyframe_insert(data_path="rotation_quaternion",frame=tick)
            bpy.context.view_layer.update()
            deps=bpy.context.evaluated_depsgraph_get()
            ev=obj.evaluated_get(deps);mesh=ev.to_mesh()
            try:
                world=[tuple(float(v) for v in obj.matrix_world@vert.co) for vert in mesh.vertices]
            finally:ev.to_mesh_clear()
            if len(world)!=48:
                raise ValueError("NATIVE_WEIGHTED_MESH_VERTEX_COUNT")
            for li,(leg,sign) in enumerate(LEGS):
                s=f["legs"][li]
                up,low=[arm.pose.bones[leg+part] for part in ("Upper","Lower")]
                observed_knee=arm.matrix_world@up.tail
                observed_ankle=arm.matrix_world@low.tail
                max_joint_error=max(max_joint_error,(observed_knee-Vector(s["knee"])).length,
                                    (observed_ankle-Vector(s["ankle"])).length)
                actual={}
                for label in ("heel","toe"):
                    idx=landmarks[leg][label]
                    point=Vector([(world[idx[0]][d]+world[idx[1]][d])/2 for d in range(3)])
                    actual[label]=[float(v) for v in point]
                    max_foot_error=max(max_foot_error,(point-Vector(s[label])).length)
                bottom=min(world[idx][2] for idx in landmarks[leg]["all_sole"])
                min_native_sole=min(bottom,min_native_sole)
                key=(ACTORS[ai][0],leg)
                if s["state"]=="stance":
                    stance_count+=1
                    if abs(bottom)>.001:
                        raise ValueError("NATIVE_WEIGHTED_STANCE_NOT_GROUNDED")
                    foot=Vector(actual["heel"])
                    if key in prior_stance:
                        slip=(foot-prior_stance[key]).length
                        max_native_stance_slip=max(max_native_stance_slip,slip)
                        if slip>.001:
                            raise ValueError("NATIVE_STANCE_SKATE")
                    prior_stance[key]=foot
                elif s["state"]=="swing":
                    swing_count+=1
                    if bottom<.019:
                        raise ValueError("NATIVE_SWING_TOO_LOW")
                    prior_stance.pop(key,None)
                else:raise ValueError("C4_CONTACT_STATE")
                actor_sample["legs"].append({"id":leg,"state":s["state"],
                     "heel":actual["heel"],"toe":actual["toe"],
                     "sole_min_z":bottom,"anchor":s["anchor"]})
            sample["actors"].append(actor_sample)
        witness.append(sample)
    if stance_count!=48 or swing_count!=48 or max_joint_error>.001 or max_foot_error>.001:
        raise ValueError("NATIVE_24FRAME_SOURCE_MISMATCH")
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    glb=out/"original_synthetic_24frame_skinned.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb.resolve()),export_format="GLB",export_animations=True)
    blend=out/"original_source_grounded_24frame_native.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
    report={"schema":"scp.walk_w5d_native_grounded.v1",
            "status":"PASS_ORIGINAL_SOURCE_24FRAME_WEIGHTED_SKIN_FOOT_OBSERVED_ONLY",
            "rights":SOURCE,"source_sha256":hashlib.sha256((out/"source.json").read_bytes()).hexdigest(),
            "glb_sha256":hashlib.sha256(glb.read_bytes()).hexdigest(),
            "blend_sha256":hashlib.sha256(blend.read_bytes()).hexdigest(),
            "profile":profile,"frame_count":24,"fps_num":12,"fps_den":1,
            "actors":2,"leg_chains":4,"stance_observations":stance_count,
            "swing_observations":swing_count,
            "max_native_joint_error":max_joint_error,
            "max_native_foot_landmark_error":max_foot_error,
            "max_native_planted_heel_slip":max_native_stance_slip,
            "min_native_sole_z":min_native_sole,
            "human_anatomy":"UNKNOWN_NO_INDEPENDENT_JCS_OR_ROM",
            "original_w7a_actor_root_motion":"SOURCE_X_APPROACH_0.33_EACH",
            "true_natural_knee_rom":"UNKNOWN_SOURCE_SAGITTAL_POLE_ONLY",
            "force_dynamics":"UNKNOWN_NO_TORQUE_OR_FORCE_MODEL",
            "actual_multi_camera_video":"NOT_RENDERED",
            "full_body":"FAIL_ABSTRACT_LIMBS_ONLY"}
    (out/"source_motion_receipt.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    (out/"evaluated_sole_24frame.json").write_text(json.dumps(witness,sort_keys=True,indent=2)+"\n")
    print("W5D_NATIVE_SOURCE_GROUNDED_24F",json.dumps(report,sort_keys=True))
    return report
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True);p.add_argument("--profile",required=True)
    p.add_argument("--out",required=True);a=p.parse_args()
    source=json.loads(Path(a.source).read_text())
    animate(source,a.profile,a.out)
