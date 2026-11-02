#!/usr/bin/env python3
"""Actual Blender 4.5 and pinned upstream MMD Tools VMD native import of an authored fixture.
NOT native MMD application playback, authentic source motion, or protected R009 acceptance.
"""
import hashlib, json, math, os, pathlib, sys
args=sys.argv[sys.argv.index("--")+1:]
if len(args)!=3: raise SystemExit("arguments: <vmd> <upstream_mmd_tools_repo> <receipt.json>")
vmd_path,upstream,output=map(pathlib.Path,args)
sys.path.insert(0,str(upstream.resolve()))
import bpy
from mmd_tools.core import vmd as upstream_vmd
from mmd_tools.core.vmd.importer import VMDImporter

data=vmd_path.read_bytes()
raw_hash=hashlib.sha256(data).hexdigest()
up=upstream_vmd.File()
up.load(filepath=str(vmd_path.resolve()))
names=("Center","L_Ankle","R_Ankle")
if set(up.boneAnimation)!=set(names):raise AssertionError("upstream MMD Tools VMD parser mismatched 3 synthetic bone names")
for name in names:
 keys=up.boneAnimation[name]
 if len(keys)!=31 or [x.frame_number for x in keys]!=list(range(31)):
  raise AssertionError("upstream MMD Tools source frame index/count mismatch")
 if any(any(not math.isfinite(float(z)) for z in x.location+x.rotation) for x in keys):
  raise AssertionError("upstream MMD Tools nonfinite keyframes")
 if abs(keys[0].location[0])>1e-6 or abs(keys[-1].location[0]-1.)>1e-6:
  raise AssertionError("source-binary endpoint mismatch")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
arm_data=bpy.data.armatures.new("SCP_Original_Synthetic")
arm=bpy.data.objects.new("SCP_Original_Synthetic_Armature",arm_data)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
for name,head,tail in (
 ("Center",(0.,0.,0.),(0.,0.,.4)),
 ("L_Ankle",(-.3,0.,-.2),(-.3,0.,0.)),
 ("R_Ankle",(.3,0.,-.2),(.3,0.,0.)),
):
 b=arm_data.edit_bones.new(name);b.head=head;b.tail=tail
bpy.ops.object.mode_set(mode="OBJECT")
for bone in arm.pose.bones:bone.rotation_mode="QUATERNION"

# Real Blender armature + two distinct skinned quad meshes; no anatomy claim.
meshes=[]
for i,name in enumerate(names[1:]):
 mesh=bpy.data.meshes.new(name+"_skinned_quad")
 center=-.3 if i==0 else .3
 mesh.from_pydata([(center-.06,-.05,-.2),(center+.06,-.05,-.2),
                   (center+.06,.05,-.2),(center-.06,.05,-.2)],[],[(0,1,2,3)])
 ob=bpy.data.objects.new(name+"_skinned_quad",mesh)
 bpy.context.scene.collection.objects.link(ob)
 vg=ob.vertex_groups.new(name=name)
 vg.add(list(range(4)),1.,"REPLACE")
 mod=ob.modifiers.new("ActualArmatureDeform","ARMATURE")
 mod.object=arm
 meshes.append(ob)

# Invoke the actual third-party Blender MMD Tools motion importer, not our decoder.
bpy.context.scene.frame_set(0)
importer=VMDImporter(str(vmd_path.resolve()),scale=1.0,frame_margin=0)
importer.assign(arm)
if not arm.animation_data or not arm.animation_data.action:
 raise AssertionError("NO_NATIVE_BLENDER_MMD_TOOLS_ACTION")
action=arm.animation_data.action

def snapshot(frame):
 bpy.context.scene.frame_set(frame)
 bpy.context.view_layer.update()
 poses={}
 for name in names:
  p=arm.pose.bones[name]
  poses[name]=tuple(float(x) for x in p.location)
 deforms={}
 dg=bpy.context.evaluated_depsgraph_get()
 for ob in meshes:
  evaluated=ob.evaluated_get(dg)
  actual=evaluated.to_mesh()
  try:
   c=[sum(float(v.co[k]) for v in actual.vertices)/len(actual.vertices) for k in range(3)]
   deforms[ob.name]=c
  finally:evaluated.to_mesh_clear()
 return poses,deforms

start,start_mesh=snapshot(0)
end,end_mesh=snapshot(30)
distances={}
for name in names:
 a,b=start[name],end[name]
 d=math.dist(a,b);distances[name]=d
 if not (0.99<=d<=1.01):raise AssertionError(f"REAL_VMD_NATIVE_POSE_NO_1_UNIT_MOTION {name} {a} {b}")
mesh_shift={}
for ob in meshes:
 name=ob.name
 d=math.dist(start_mesh[name],end_mesh[name])
 mesh_shift[name]=d
 if not (0.99<=d<=1.01):raise AssertionError(f"REAL_BLENDER_ARMATURE_SKIN_NO_1_UNIT_DEFORMATION {name} {d}")

# Independent reverse-time playback; at frame 0 the Blender evaluator must return to start.
p0,m0=snapshot(0)
for name in names:
 if math.dist(p0[name],start[name])>1e-6:raise AssertionError("FRAME_REWIND_NOT_IDEMPOTENT")
for key in m0:
 if math.dist(m0[key],start_mesh[key])>1e-6:raise AssertionError("SKIN_FRAME_REWIND_NOT_IDEMPOTENT")

report={
 "schema":"scp.mmd.actual_blender_mmd_tools_original_vmd.v1",
 "status":"PASS_AUTHORED_SYNTHETIC_BLENDER45_MMD_TOOLS_IMPORT_AND_ACTUAL_SKIN_DEFORM_ONLY",
 "blender_version":bpy.app.version_string,"plugin_version":"v4.5.14",
 "plugin_source_ref":"fc6411d0fb0dd690cae8cf8eb1fae14311e756cc",
 "vmd_sha256":raw_hash,"upstream_imported_tracks":3,
 "upstream_imported_keyframes_per_track":31,"native_action_name":action.name,
 "bone_frame_0_to_30_displacements":distances,
 "skinned_mesh_frame_0_to_30_displacements":mesh_shift,
 "frame0_after_rewind":"BYTE_EQUIVALENT_NUMERIC_WITH_TOLERANCE",
 "source_rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
 "measured_human_mocap":"NOT_ADMITTED",
 "genuine_PMX_MMD_target":"NOT_RUN",
 "standalone_MMD_runtime":"NOT_RUN",
 "physical_contact":"UNKNOWN","anatomy_JCS_ROM":"UNKNOWN",
 "private_R009":"HELD_NOT_RUN_NOT_ADMITTED"
}
output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
print("PASS_AUTHORED_SYNTHETIC_NATIVE_BLENDER_AND_MMD_TOOLS_IMPORT",json.dumps(report,sort_keys=True))
