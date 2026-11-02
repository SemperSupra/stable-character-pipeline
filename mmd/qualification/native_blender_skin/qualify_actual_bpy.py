#!/usr/bin/env python3
"""Actual bpy armature + upstream MMD Tools VMDImporter on an authored VMD.
NOT private character, anatomical, PMX, standalone MMD, or native real gait.
"""
import hashlib,json,math,pathlib,sys

if "--" not in sys.argv:raise SystemExit("missing isolated Blender -- args")
args=sys.argv[sys.argv.index("--")+1:]
if len(args)!=3:raise SystemExit("expected authored.vmd, upstream source root, output.json")
source,upstream,out=map(pathlib.Path,args)
raw=source.read_bytes()
sha=hashlib.sha256(raw).hexdigest()
if sha!="3b20c6822337dab0078d32a2d65f7ead2d11716db5e5500b619d3218b4439b94":
 raise RuntimeError("NATIVE_BLENDER_UNADMITTED_ORIGINAL_VMD_SHA")

import bpy
import tempfile,zipfile
# The unmodified add-on manifest declares this exact bundled wheel. Its
# OpenCC dictionary loader uses filesystem paths (not zipimport paths), so
# extract it into an ephemeral sandbox rather than import the .whl directly.
wheel=upstream/"mmd_tools"/"wheels"/"opencc_python_reimplemented-0.1.7-py2.py3-none-any.whl"
if not wheel.is_file():raise RuntimeError("PINNED_UPSTREAM_OPENCC_WHEEL_MISSING")
wheel_root=pathlib.Path(tempfile.mkdtemp(prefix="scp-mmd-opencc-"))
with zipfile.ZipFile(wheel) as archive:
 members=archive.infolist()
 if len(members)>3000:raise RuntimeError("UNBOUNDED_UPSTREAM_WHEEL_MEMBERS")
 for member in members:
  p=pathlib.PurePosixPath(member.filename)
  if p.is_absolute() or ".." in p.parts or member.file_size>10_000_000:
   raise RuntimeError("UPSTREAM_WHEEL_EXTRACTION_UNSAFE")
 archive.extractall(wheel_root)
sys.path.insert(0,str(wheel_root))
sys.path.insert(0,str(upstream.resolve()))
from mmd_tools.core.vmd.importer import VMDImporter
from mmd_tools.core import vmd as upstream_reader

src=upstream_reader.File()
src.load(filepath=str(source.resolve()))
names=("Center","L_Ankle","R_Ankle")
if set(src.boneAnimation)!=set(names):
 raise AssertionError("UPSTREAM_SOURCE_NAMES_MISMATCH")
if any(len(src.boneAnimation[n])!=31 for n in names):
 raise AssertionError("UPSTREAM_SOURCE_CLOCK_NOT_31_FRAMES")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.context.scene.frame_set(0)
arm_data=bpy.data.armatures.new("SCP_Original_Synthetic")
arm=bpy.data.objects.new("SCP_Original_Synthetic_Armature",arm_data)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
for name,head,tail in (
 ("Center",(0.,0.,0.),(0.,0.,.5)),
 ("L_Ankle",(-.3,0.,-.2),(-.3,0.,.0)),
 ("R_Ankle",(.3,0.,-.2),(.3,0.,.0)),
):
 b=arm_data.edit_bones.new(name)
 b.head=head
 b.tail=tail
bpy.ops.object.mode_set(mode="OBJECT")
for b in arm.pose.bones:b.rotation_mode="QUATERNION"

# Real Blender ARMATURE modifiers on genuinely authored primitive mesh geometry.
# No protected skin, identity likeness or implicit acceptance.
meshes=[]
for name,x in (("L_Ankle",-.3),("R_Ankle",.3)):
 data=bpy.data.meshes.new(name+"_quad")
 data.from_pydata([(x-.08,-.05,-.2),(x+.08,-.05,-.2),
                   (x+.08,.05,-.2),(x-.08,.05,-.2)],[],[(0,1,2,3)])
 ob=bpy.data.objects.new(name+"_deformed_quad",data)
 bpy.context.scene.collection.objects.link(ob)
 vgroup=ob.vertex_groups.new(name=name)
 vgroup.add([0,1,2,3],1.0,"REPLACE")
 deform=ob.modifiers.new("ActualBlenderArmature","ARMATURE")
 deform.object=arm
 meshes.append(ob)

# This is the REAL plugin importer into native bpy action curves, not an
# approximation or independently written VMD→rig shortcut.
imp=VMDImporter(str(source.resolve()),scale=1.0,frame_margin=0)
imp.assign(arm)
action=arm.animation_data.action if arm.animation_data else None
if action is None:raise AssertionError("NATIVE_MMD_TOOLS_NO_ARMATURE_ACTION")

def sample(frame):
 bpy.context.scene.frame_set(frame)
 bpy.context.view_layer.update()
 pose={name:tuple(float(v) for v in arm.pose.bones[name].location) for name in names}
 dg=bpy.context.evaluated_depsgraph_get()
 mesh_positions={}
 for ob in meshes:
  eob=ob.evaluated_get(dg)
  edata=eob.to_mesh()
  try:
   if len(edata.vertices)!=4:raise AssertionError("NATIVE_SKIN_MISSING_EVALUATED_VERTICES")
   mesh_positions[ob.name]=tuple(
      sum(float(v.co[k]) for v in edata.vertices)/4. for k in range(3))
  finally:eob.to_mesh_clear()
 return pose,mesh_positions

pose0,mesh0=sample(0)
pose30,mesh30=sample(30)
pose_reset,mesh_reset=sample(0)
joint_deltas={name:math.dist(pose0[name],pose30[name]) for name in names}
skin_deltas={name:math.dist(mesh0[name],mesh30[name]) for name in mesh0}
for name,d in joint_deltas.items():
 if not math.isfinite(d) or not .9<=d<=1.1:
  raise AssertionError("NATIVE_BLENDER_MMD_TOOLS_JOINT_NO_AUTHORED_MOTION_"+name+":"+str(d))
for name,d in skin_deltas.items():
 if not math.isfinite(d) or not .9<=d<=1.1:
  raise AssertionError("NATIVE_BLENDER_ARMATURE_MESH_DEFORM_NO_MOTION_"+name+":"+str(d))
for name in names:
 if math.dist(pose0[name],pose_reset[name])>1e-7:
  raise AssertionError("NATIVE_BLENDER_POSE_REWIND_NOT_IDEMPOTENT")
for name in mesh0:
 if math.dist(mesh0[name],mesh_reset[name])>1e-7:
  raise AssertionError("NATIVE_BLENDER_MESH_REWIND_NOT_IDEMPOTENT")
r={"schema":"scp.mmd.native_bpy_original_skin.v1",
 "status":"PASS_ACTUAL_BLENDER45_MMD_TOOLS_VMD_IMPORT_AND_SYNTHETIC_SKIN_ONLY",
 "original_vmd_sha256":sha,"blender_version":bpy.app.version_string,
 "mmd_tools_commit":"f1d8a98db5e185cfa73c9b8a8a67fa42d9eb4b14",
 "importer":"mmd_tools.core.vmd.importer.VMDImporter.assign",
 "source_keyframes":93,"actual_bpy_pose_track_count":len(names),
 "actual_skinned_meshes":len(meshes),"actual_bpy_action":str(action.name),
 "frame_0_to_30_joint_displacement":joint_deltas,
 "frame_0_to_30_skinned_mesh_displacement":skin_deltas,
 "frame0_rewind":"PASS_NUMERIC_TOLERANCE_1E_MINUS_7",
 "source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
 "human_mocap":"NOT_ADMITTED","native_standalone_MMD":"NOT_RUN",
 "PMX_specific_rig":"NOT_RUN","genuine_human_skin":"NOT_RUN",
 "visual_gait":"UNKNOWN","anatomy_rom_jcs":"UNKNOWN",
 "protected_R009":"HELD_NOT_ACCEPTED"}
with out.open("x",encoding="utf8") as f:
 json.dump(r,f,indent=2,sort_keys=True)
 f.write("\n")
print("PASS_NATIVE_ORIGINAL_SYNTHETIC_ARMATURE_SKIN",json.dumps(r,sort_keys=True))
