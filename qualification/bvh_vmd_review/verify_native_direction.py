#!/usr/bin/env python3
"""Independent native signed-axis and evaluated skin witness for self-authored BVH fixture.

Runs reviewed producer/importer unmodified, then inspects actual bpy evaluated
pose/mesh after each source endpoint. No human skeleton or real retargeting claim.
"""
import bpy,hashlib,json,math,pathlib,runpy,sys

args=sys.argv[sys.argv.index("--")+1:]
if len(args)!=5:
    raise SystemExit("Expected original VMD, pinned upstream, crosswalk JSON, FK JSON, receipt output")
vmd,upstream,crosswalk,fkfile,output=map(pathlib.Path,args)
fkraw=fkfile.read_bytes()
fk=json.loads(fkraw); cross=json.loads(crosswalk.read_bytes())
if cross.get("fk_receipt_sha256")!=hashlib.sha256(fkraw).hexdigest():
    raise RuntimeError("NATIVE_REVIEW_FK_CUSTODY_MISMATCH")
if cross.get("source_frame_1")!="DROPPED_30FPS_RESAMPLE":
    raise RuntimeError("NATIVE_REVIEW_LOSS_MAP_MISSING")
if cross.get("private_R009")!="HELD_NOT_ACCEPTED":
    raise RuntimeError("NATIVE_REVIEW_PRODUCT_PROMOTION")

import sys as _sys
argv_before=_sys.argv[:]
import tempfile
producer_receipt=pathlib.Path(tempfile.mkdtemp(prefix="scp-review-"))/"native-original.json"
try:
    _sys.argv=["blender","--",str(vmd),str(upstream),str(crosswalk),str(producer_receipt)]
    runpy.run_path(str(pathlib.Path("qualification/bvh_vmd_bridge/native_crosswalk.py").resolve()),run_name="__main__")
finally:
    _sys.argv=argv_before
producer=json.loads(producer_receipt.read_text())
if producer["status"]!="PASS_ACTUAL_BPY_MMD_TOOLS_AUTHORED_BVH_CROSSWALK_ONLY":
    raise RuntimeError("NATIVE_REVIEW_PRODUCER_NOT_GREEN")
arm=bpy.data.objects.get("OriginalBVH3")
if arm is None or arm.type!="ARMATURE":
    raise RuntimeError("NATIVE_REVIEW_ACTUAL_BPY_ARMATURE_MISSING")
jointnames=("Hips","Knee","Foot")
if set(b.name for b in arm.pose.bones)!=set(jointnames):
    raise RuntimeError("NATIVE_REVIEW_UNEXPECTED_RIG")
def evaluate(frame):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    result={}
    for n in jointnames:
        ob=bpy.data.objects.get(n+"_mesh")
        if ob is None or sum(m.type=="ARMATURE" and m.object==arm for m in ob.modifiers)!=1:
            raise RuntimeError("NATIVE_REVIEW_SKIN_MODIFIER_MISSING:"+n)
        dg=bpy.context.evaluated_depsgraph_get()
        ev=ob.evaluated_get(dg)
        mesh=ev.to_mesh()
        try:
            if len(mesh.vertices)!=4:raise RuntimeError("NATIVE_REVIEW_SKIN_VERTICES_MISSING")
            center=tuple(sum(float((ev.matrix_world@v.co)[k]) for v in mesh.vertices)/4 for k in range(3))
        finally:ev.to_mesh_clear()
        result[n]={"pose_xyz":tuple(float(x) for x in arm.pose.bones[n].location),"skin_center_xyz":center}
    return result
start=evaluate(0)
end=evaluate(1)
reset=evaluate(0)
out={}
for i,n in enumerate(jointnames):
    src0=fk["frames"][0]["world_joints"][i]["position_meters"]
    src2=fk["frames"][2]["world_joints"][i]["position_meters"]
    expected=[src2[k]-src0[k] for k in range(3)]
    if expected!=[1.0,0.0,0.0]:
        raise RuntimeError("NATIVE_REVIEW_UNEXPECTED_ORIGINAL_FK_FIXTURE:"+n)
    pose_diff=[end[n]["pose_xyz"][k]-start[n]["pose_xyz"][k] for k in range(3)]
    skin_diff=[end[n]["skin_center_xyz"][k]-start[n]["skin_center_xyz"][k] for k in range(3)]
    maxpose=max(abs(pose_diff[k]-expected[k]) for k in range(3))
    maxskin=max(abs(skin_diff[k]-expected[k]) for k in range(3))
    reseterror=max(abs(reset[n]["pose_xyz"][k]-start[n]["pose_xyz"][k]) for k in range(3))
    if maxpose>1e-5:raise RuntimeError("NATIVE_REVIEW_SIGNED_AXIS_FALSE_ACCEPT:"+n)
    if maxskin>1e-5:raise RuntimeError("NATIVE_REVIEW_SIGNED_SKIN_FALSE_ACCEPT:"+n)
    if reseterror>1e-7:raise RuntimeError("NATIVE_REVIEW_POSE_REWIND_FALSE_ACCEPT:"+n)
    out[n]={"source_world_delta_m":expected,
            "observed_native_pose_delta_m":pose_diff,
            "observed_native_skin_delta_m":skin_diff,
            "max_signed_axis_error_m":maxpose,"max_signed_skin_error_m":maxskin,
            "pose_rewind_error_m":reseterror}
receipt={"schema":"scp.r009.independent-bpy-signed-axes.v1",
         "status":"PASS_PUBLIC_ORIGINAL_SYNTHETIC_SIGNED_BPY_TRANSLATION_AND_SKIN_ONLY",
         "vmd_sha256":hashlib.sha256(vmd.read_bytes()).hexdigest(),
         "source_fk_receipt_sha256":hashlib.sha256(fkraw).hexdigest(),
         "actual_blender_version":bpy.app.version_string,
         "observed_native":out,
         "source_to_target":"ORIGINAL_AUTHORED_WORLD_TRANSLATION_ONLY",
         "retargeted_real_human_anatomy":"NOT_RUN",
         "human_JCS_ROM":"UNKNOWN","protected_R009":"HELD_NOT_ACCEPTED",
         "CPE":"NOT_PROMOTED"}
with output.open("x",encoding="utf8") as f:
    json.dump(receipt,f,sort_keys=True,indent=2)
    f.write("\n")
print("PASS_INDEPENDENT_BPY_SIGNED_AXIS_AND_SKIN",json.dumps(receipt,sort_keys=True))
