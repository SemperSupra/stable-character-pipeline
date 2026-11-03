#!/usr/bin/env python3
"""Source-safe Blender scene composition of three previously qualified public rungs.

This proves a VMD source spatial unit calibration and a separately authored
72f parented multiweight rig coexist with 2-camera synthetic H264 rendering.
IT DOES NOT retarget BVH temporal rotations into a human gait or original actor.
"""
import bpy,hashlib,json,math,pathlib,runpy,sys,tempfile
from mathutils import Vector
args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
if len(args)!=7:
    raise SystemExit("expected TRACE HIER_SPEC VMD UPSTREAM_MMD CROSSWALK FK OUTPUT")
tracepath,hierpath,vmdpath,upstream,crosswalk,fkpath,output=map(pathlib.Path,args)
output=output.resolve()
tracebytes=tracepath.read_bytes();hierbytes=hierpath.read_bytes()
trace=json.loads(tracebytes);hier=json.loads(hierbytes)
cross=json.loads(crosswalk.read_bytes());fkbytes=fkpath.read_bytes()
def sha(b):return hashlib.sha256(b).hexdigest()
def guard(ok,msg):
    if not ok:raise RuntimeError("R009_INTEGRATION_REJECT:"+msg)
guard(sha(tracebytes)=="1e56d63873b83dc33ea8f510932d1df0e09acfc66e9dae8880f2ae91658d5e86","SHADOW_SOURCE_HASH")
guard(sha(hierbytes)=="03a81c2a5ad6729f3022f4b1d4afbb94395c3a2b29b413ba601480c6995d463a","HIER_SOURCE_HASH")
guard(trace["private_r009"]=="HELD_NOT_ACCEPTED" and hier["private_R009"]=="HELD_NOT_ACCEPTED","PRIVATE_MVP_FALSE_PROMOTION")
guard(trace["source_class"]==hier["source_class"]=="ORIGINAL_SELF_AUTHORED_SYNTHETIC","UNADMITTED_SOURCE")
guard(trace["fps"]==hier["fps"]==12 and len(trace["frames"])==len(hier["frames"])==72,"SOURCE_FRAME_CLOCK")
guard(cross["fk_receipt_sha256"]==sha(fkbytes),"FOREIGN_FK_BYTES")
guard(cross["vmd_sha256"]==sha(vmdpath.read_bytes()),"FOREIGN_VMD_BYTES")
guard(cross["source_frame_1"]=="DROPPED_30FPS_RESAMPLE" and cross["target_fps"]==30,"VMD_EXPLICIT_CLOCK_LOSS")
guard(cross["synthetic_target_aliases"]=={"Hips":"Hips","Knee":"Knee","Foot":"Foot"},"TARGET_ALIAS_DRIFT")
guard(cross["hierarchy_semantics"]=="LOST_WORLD_TRANSLATION_ONLY_NOT_HUMAN_RETARGETING","FAKE_HIERARCHICAL_RETARGET")
guard(hier["physical_human_ROM"]=="UNKNOWN" and hier["real_contact_force"]=="UNKNOWN","FAKE_BIOPHYSICS")
guard(set(trace["actor_ids"])=={"CobaltOriginal","MarigoldOriginal"},"ORIGINAL_ACTOR_ROSTER")
for i,(a,b) in enumerate(zip(trace["frames"],hier["frames"])):
    guard(a["frame"]==b["frame"]==i,"FRAME_INDEX_DRIFT")

# First execute the exact already qualified upstream-native import as a real
# Blender scene and read POSE from actual bpy. No fabricated VMD parity flag.
tmp=pathlib.Path(tempfile.mkdtemp(prefix="r009-integrated-"))
adapter=tmp/"vmd-native-adapter.json"
argv=sys.argv[:]
sys.argv=["blender","--",str(vmdpath.resolve()),str(upstream.resolve()),str(crosswalk.resolve()),str(adapter)]
try:
    runpy.run_path(str(pathlib.Path("qualification/bvh_vmd_bridge/native_crosswalk.py").resolve()),run_name="__main__")
finally:
    sys.argv=argv
ar=bpy.data.objects.get("OriginalBVH3")
guard(ar is not None and ar.type=="ARMATURE","NATIVE_IMPORTED_ARMATURE_ABSENT")
def sample(frame):
    bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
    return {n:tuple(float(v) for v in ar.pose.bones[n].location) for n in ("Hips","Knee","Foot")}
before=sample(0);after=sample(1)
observed={n:[after[n][j]-before[n][j] for j in range(3)] for n in before}
for n,v in observed.items():
    guard(max(abs(v[k]-[1.,0.,0.][k]) for k in range(3))<1e-5,"SIGNED_VMD_WORLD_DELTA:"+n)
adapter_receipt=json.loads(adapter.read_bytes())
guard(adapter_receipt["status"]=="PASS_ACTUAL_BPY_MMD_TOOLS_AUTHORED_BVH_CROSSWALK_ONLY","VMD_IMPORTER_NOT_ACCEPTED")

# Second reproduce original authored two-camera scene with original source
# intact. This resets bpy and initially renders the unmodified original shadow.
sys.argv=["blender","--",str(tracepath.resolve()),str(output)]
try:
    runpy.run_path(str(pathlib.Path("qualification/shadow_park/render_native.py").resolve()),run_name="__main__")
finally:sys.argv=argv
scene=bpy.context.scene
original_scene=json.loads((output/"native_receipt.json").read_bytes())
guard(original_scene["status"]=="PASS_PUBLIC_ORIGINAL_SYNTHETIC_SKIN_AND_2CAMERA_RENDER_ONLY","ORIGINAL_SCENE_NOT_NATIVE_GREEN")
orig_frame_hash={cam:sha((output/cam/"frame_036.png").read_bytes()) for cam in ("front","oblique")}
palette={"CobaltOriginal":bpy.data.materials["CobaltOriginalTeal"],
         "MarigoldOriginal":bpy.data.materials["MarigoldOriginalOchre"]}
r={}
for actor,off in (("CobaltOriginal",-.085),("MarigoldOriginal",.085)):
    newname=actor+"_IntegralHierRig"
    ad=bpy.data.armatures.new(newname+"_bones");arm=bpy.data.objects.new(newname,ad)
    scene.collection.objects.link(arm)
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True);bpy.context.view_layer.objects.active=arm
    bpy.ops.object.mode_set(mode="EDIT")
    th=ad.edit_bones.new("thigh");th.head=(off,0,1.1);th.tail=(off,0,.6)
    sh=ad.edit_bones.new("shin");sh.head=th.tail;sh.tail=(off,0,.12)
    sh.parent=th;sh.use_connect=True
    foot=ad.edit_bones.new("foot");foot.head=sh.tail;foot.tail=(off,.20,.12)
    foot.parent=sh;foot.use_connect=True
    bpy.ops.object.mode_set(mode="OBJECT");arm.select_set(False)
    for pb in arm.pose.bones:pb.rotation_mode="XYZ"
    mesh=bpy.data.meshes.new(newname+"_blend")
    mesh.from_pydata([(off-.06,0,.90),(off+.06,0,.90),
        (off-.07,0,.6),(off+.07,0,.6),
        (off-.05,0,.38),(off+.05,0,.38)],[],[(0,1,3,2),(2,3,5,4)])
    ob=bpy.data.objects.new(newname+"_ActualDualSkinned",mesh)
    scene.collection.objects.link(ob);mesh.materials.append(palette[actor])
    upper=ob.vertex_groups.new(name="thigh")
    lower=ob.vertex_groups.new(name="shin")
    upper.add([0,1],1.0,"REPLACE")
    upper.add([2,3],.5,"REPLACE")
    lower.add([2,3],.5,"REPLACE")
    lower.add([4,5],1.0,"REPLACE")
    mod=ob.modifiers.new("VerifiedNativeArmature","ARMATURE");mod.object=arm
    guard(ad.bones["shin"].parent==ad.bones["thigh"] and
          ad.bones["foot"].parent==ad.bones["shin"],"HIERARCHY_NOT_PARENTED")
    for v in mesh.vertices:
        weights=[g.weight for g in v.groups]
        guard(abs(sum(weights)-1)<1e-7,"NONNORMALIZED_EVALUATED_VERTEX_DENOMINATOR")
        if v.index in (2,3):
            guard(len(weights)==2 and min(weights)>.1,"NOT_DUAL_WEIGHT")
    # VMD is consumed only as a measured spatial calibration, NOT used to
    # invent six seconds of BVH source rotation or resample its 30Hz 2 keys.
    meter_gain=observed["Hips"][0]
    guard(abs(meter_gain-1)<1e-5,"VMD_UNIT_CALIBRATION")
    arm.scale.x=meter_gain
    for i,(frame,pose) in enumerate(zip(trace["frames"],hier["frames"])):
        arm.location.x=frame["actors"][actor]["root_x_m"]
        arm.keyframe_insert(data_path="location",frame=i)
        arm.pose.bones["thigh"].rotation_euler=(math.radians(pose["hip_deg"]),0,0)
        arm.pose.bones["shin"].rotation_euler=(math.radians(pose["knee_deg"]),0,0)
        for bn in ("thigh","shin"):
            arm.pose.bones[bn].keyframe_insert(data_path="rotation_euler",frame=i)
    r[actor]={"connected_edges":2,"blended_knee_vertices":2,
              "source_to_native_meter_gain":meter_gain}
    def points(frame):
        scene.frame_set(frame);bpy.context.view_layer.update()
        ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
        m=ev.to_mesh()
        try:return [tuple(ev.matrix_world @ v.co) for v in m.vertices]
        finally:ev.to_mesh_clear()
    p0=points(0);p6=points(6);pr=points(0)
    moved=max(math.dist(a,b) for a,b in zip(p0,p6))
    rewind=max(math.dist(a,b) for a,b in zip(p0,pr))
    guard(moved>.015 and rewind<1e-6,"NATIVE_HIER_SKIN_FROZEN_OR_NONREWIND")
    r[actor]["actual_evaluated_skin_motion_f0_f6_m"]=moved
    r[actor]["rewind_error_m"]=rewind

debug_markers=[o for o in bpy.data.objects if o.name.endswith("_ground_truth_PLANTED") or o.name.endswith("_ground_truth_SWING")]
guard(len(debug_markers)==8,"DEBUG_FOOT_MARKER_ROSTER")
# The upstream authored renderer keys hide_render on every frame. Blender may
# reevaluate that FCurve while rendering, overriding manually chosen clean/debug
# visibility. Remove animation only on the eight debug-only marker objects;
# their locations and booleans are rebuilt from the ORIGINAL immutable trace
# for every debug frame. Actor motions and the two native rigs stay unchanged.
for marker in debug_markers:marker.animation_data_clear()
cameras={"front":bpy.data.objects["front_OriginalCamera"],
         "oblique":bpy.data.objects["oblique_OriginalCamera"]}
# Rerender original clean views WITH the newly added real weighted hierarchy,
# always suppressing all debug-only markers during these clean frames.
for cam in ("front","oblique"):
    scene.camera=cameras[cam]
    for i in range(72):
        scene.frame_set(i)
        for o in debug_markers:o.hide_render=True
        bpy.context.view_layer.update()
        guard(all(o.hide_render for o in debug_markers),"CLEAN_CAMERA_DEBUG_MARKER_LEAK")
        scene.render.filepath=str(output/cam/("frame_%03d.png"%i))
        bpy.ops.render.render(write_still=True)
for cam in ("front","oblique"):
    guard(sha((output/cam/"frame_036.png").read_bytes())!=orig_frame_hash[cam],
          "INTEGRATED_SKIN_DID_NOT_CHANGE_ENCODED_CAMERA:"+cam)
# For debug, force exact authored planted/swing visibility AFTER frame updates.
scene.camera=cameras["front"]
for i,frame in enumerate(trace["frames"]):
    scene.frame_set(i)
    for o in debug_markers:
        actor=next((a for a in trace["actor_ids"] if o.name.startswith(a+"_")),None)
        guard(actor is not None,"UNKNOWN_DEBUG_MARKER")
        side="left" if "_left_" in o.name else "right"
        is_contact=o.name.endswith("_ground_truth_PLANTED")
        state=frame["actors"][actor]["feet"][side]
        o.location=state["ankle"]
        o.hide_render=(state["contact"] != is_contact)
    bpy.context.view_layer.update()
    guard(sum(not o.hide_render for o in debug_markers)==4,"DEBUG_FOOT_VISIBILITY_STATE_MISSING")
    scene.render.filepath=str(output/"debug_front"/("frame_%03d.png"%i))
    bpy.ops.render.render(write_still=True)

result={"schema":"scp.r009.original-synthetic-integrated-native-park.v1",
 "status":"PASS_COMPOSED_ORIGINAL_SYNTHETIC_SOURCE_VMD_CALIBRATION_HIER_SKIN_AND_TWO_CAMERA",
 "original_source_sha256":sha(tracebytes),"hier_source_sha256":sha(hierbytes),
 "vmd_source_sha256":sha(vmdpath.read_bytes()),"source_fk_sha256":sha(fkbytes),
 "blender":bpy.app.version_string,
 "vmd_imported_original_bpy_signed_delta_xyz":observed,
 "parented_real_multiweight_rigs":r,"original_native_scene_receipt":original_scene["schema"],
 "original_source_actors":list(trace["actor_ids"]),
 "views":{"front":72,"oblique":72,"debug_front":72},"fps":12,
 "vmd_input_source_fps":60,"vmd_target_fps":30,"vmd_source_middle_frame":"EXPLICITLY_DROPPED",
 "vmd_to_hier_usage":"SPATIAL_CALIBRATION_ONLY_NO_TEMPORAL_HUMAN_RETARGET",
 "72f_hier_pose_source":"SEPARATE_ORIGINAL_SYNTHETIC_FIXTURE_HIP_KNEE_ONLY",
 "physical_biomechanics":"UNKNOWN","original_identity":"NOT_ADMITTED",
 "protected_R009":"HELD_NOT_ACCEPTED","CPE":"NOT_PROMOTED"}
with (output/"integrated_native_receipt.json").open("x") as f:
    json.dump(result,f,sort_keys=True,indent=2);f.write("\n")
print("PASS_ORIGINAL_INTEGRATED_NATIVE_SAFEGUARDED",json.dumps(result,sort_keys=True))
