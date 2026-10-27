#!/usr/bin/env python3
"""G10c genuine MMD Tools Blender IK import: measure goal tracking separately."""
import argparse
import json
import math
import os
from pathlib import Path
import sys

def main():
    ap=argparse.ArgumentParser()
    for k in ("source","model","motion","out"):
        ap.add_argument("--"+k,type=Path,required=True)
    a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    import bpy
    assert bpy.app.version >= (4,2,0),bpy.app.version_string
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sys.path.insert(0,str(a.source.resolve()))
    import mmd_tools
    mmd_tools.register()
    result=bpy.ops.mmd_tools.import_model(
      filepath=str(a.model.resolve()),types={"MESH","ARMATURE","PHYSICS"},
      scale=1.0,rename_bones=False,fix_bone_order=False)
    assert "FINISHED" in result,result
    rigs=[o for o in bpy.data.objects if o.type=="ARMATURE"]
    assert len(rigs)==1,[o.name for o in rigs]
    rig=rigs[0]
    names=["腰","ひざ","足首","足ＩＫ"]
    assert all(n in rig.pose.bones for n in names),list(rig.pose.bones.keys())
    constraint_info={}
    for b in rig.pose.bones:
        cs=[]
        for c in b.constraints:
            target=getattr(c,"target",None)
            cs.append({"type":c.type,"name":c.name,"muted":bool(c.mute),
              "target_object":target.name if target is not None else None,
              "subtarget":getattr(c,"subtarget",None),
              "chain_count":getattr(c,"chain_count",None),
              "iterations":getattr(c,"iterations",None)})
        constraint_info[b.name]=cs
    rest_heads={n:[float(v) for v in rig.data.bones[n].head_local] for n in names}
    rest_tails={n:[float(v) for v in rig.data.bones[n].tail_local] for n in names}
    ik_constraints=[(n,c) for n,p in [(n,rig.pose.bones[n]) for n in names]
        for c in p.constraints if c.type=="IK"]
    print("G10C_IMPORT_CONSTRAINTS",json.dumps(constraint_info,sort_keys=True),flush=True)
    print("G10C_BONE_REST",json.dumps({"heads":rest_heads,"tails":rest_tails},sort_keys=True),flush=True)
    # PMX source frame zero must remain zero in Blender, not shifted to scene frame1.
    bpy.context.scene.frame_set(0)
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active=rig
    imported=bpy.ops.mmd_tools.import_vmd(
        filepath=str(a.motion.resolve()),scale=1.0,
        margin=0,bone_mapper="PMX",update_scene_settings=False)
    assert "FINISHED" in imported,imported
    scene=bpy.context.scene
    scene.frame_start,scene.frame_end=0,30
    scene.render.fps=30
    samples={}
    for frame in (0,15,30):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        deps=bpy.context.evaluated_depsgraph_get()
        evaluated=rig.evaluated_get(deps)
        # Blender pose-bone matrix is evaluated armature-local; common rig frame,
        # so Euclidean ankle->controller distance is invariant to the object transform.
        ankle=evaluated.pose.bones["足首"].matrix.translation
        goal=evaluated.pose.bones["足ＩＫ"].matrix.translation
        hip=evaluated.pose.bones["腰"].matrix.translation
        sample={
          "ankle_xyz":[float(x) for x in ankle],
          "goal_xyz":[float(x) for x in goal],
          "hip_xyz":[float(x) for x in hip],
          "error":float((ankle-goal).length)
        }
        samples[str(frame)]=sample
    print("G10C_EVALUATED_IK",json.dumps(samples,sort_keys=True),flush=True)
    assert math.dist(samples["0"]["goal_xyz"],samples["30"]["goal_xyz"])>.15,"source IK target did not move"
    # Require correct IK setup and nonzero real motion before contact claims.
    if not ik_constraints:
        raise AssertionError("MMD IK bone source imported, but Blender IK constraint not assembled")
    path=a.out/"blender_ik_source.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path.resolve()))
    assert path.stat().st_size>1000
    # No target-tracking threshold here: this gate measures real Blender solver,
    # with separate follow-on parity against source converter and native MMD.
    report={
      "schema":"scp.mmd.ik.blender.v1",
      "status":"PASS_REAL_BLENDER_MMD_IK_CONSTRAINT_AND_GOAL_MOTION",
      "blender":bpy.app.version_string,
      "mmd_tools":mmd_tools.MMD_TOOLS_VERSION,
      "constraint_info":constraint_info,
      "rest_heads":rest_heads,
      "rest_tails":rest_tails,
      "real_ik_constraint_count":len(ik_constraints),
      "samples":samples,
      "scope":"true imported Blender IK + native VMD goal, not MMD CCD equivalence or collision",
      "unqualified":["quantified Blender/native solver parity","foot lock tolerance","friction","ground reaction","realistic gait"]
    }
    (a.out/"blender_ik_receipt.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="constraint_info"},sort_keys=True),flush=True)

if __name__=="__main__":
    try:
        main()
    except BaseException:
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
