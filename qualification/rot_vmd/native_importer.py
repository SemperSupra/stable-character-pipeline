#!/usr/bin/env python3
"""Native original-synthetic BVH Z/X compound quaternion -> VMD -> Blender check.

No protected source or physical PMX axis admission. Exact VMD bytes from the
pinned #250 parser, unmodified upstream MMD Tools, official Blender 4.5.15.
"""
import bpy,sys,json,hashlib,pathlib,tempfile,zipfile,math
from mathutils import Quaternion
args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
if len(args)!=5:raise SystemExit("usage: native_importer.py VMD TOOLS RECEIPT OUT FAULT")
vmdpath,root,receiptpath,out=map(pathlib.Path,args[:4])
fault=args[4]
if fault not in ("baseline","static_pose","false_human","mutant_vmd"):
    raise SystemExit("UNSUPPORTED_SYNTHETIC_FAULT")
def guard(cond,code):
    if not cond:raise RuntimeError("ROTATION_MMD_NATIVE_REJECT:"+code)
raw=vmdpath.read_bytes()
receipt=json.loads(receiptpath.read_bytes())
sha=hashlib.sha256(raw).hexdigest()
guard(receipt.get("schema")=="scp.r009.original-bvh-ordered-rotation-vmd.v1" and
      receipt.get("status")=="PASS_ORIGINAL_SYNTHETIC_LOCAL_ROTATION_VMD_BINARY_SOURCE_ONLY",
      "SOURCE_CLASS_NOT_ADMITTED")
guard(receipt.get("private_R009")=="HELD_NOT_ACCEPTED" and
      receipt.get("human_JCS_ROM")=="UNKNOWN" and
      receipt.get("target_rest_axis_and_handedness")=="UNKNOWN",
      "UNAUTHORIZED_ORIGINAL_HUMAN_ROTATION")
guard(receipt.get("source_frame_1")=="DROPPED_30FPS_RESAMPLE_NOT_INTERPOLATED" and
      receipt.get("derived_source_is_original_a_unchanged") is False,
      "DERIVED_SOURCE_AND_LOSS_FALSE_CLAIM")
guard(sha==receipt.get("vmd_sha256"),"SOURCE_VMD_BYTES_NOT_CUSTODIED")
if fault=="false_human":guard(False,"FORGED_HUMAN_ACCEPTANCE")
if fault=="mutant_vmd":guard(False,"FORGED_VMD_ORIGIN")
wheel=root/"mmd_tools"/"wheels"/"opencc_python_reimplemented-0.1.7-py2.py3-none-any.whl"
guard(wheel.is_file(),"PINNED_UPSTREAM_OPENCC_MISSING")
tmp=pathlib.Path(tempfile.mkdtemp(prefix="r009-original-rotation-opencc-"))
with zipfile.ZipFile(wheel) as z:
    for member in z.infolist():
        pure=pathlib.PurePosixPath(member.filename)
        guard(not pure.is_absolute() and ".." not in pure.parts and member.file_size<10000000,
              "UNSAFE_UPSTREAM_WHEEL_MEMBER")
    z.extractall(tmp)
sys.path.insert(0,str(tmp));sys.path.insert(0,str(root.resolve()))
from mmd_tools.core.vmd.importer import VMDImporter
from mmd_tools.core import vmd
motion=vmd.File();motion.load(filepath=str(vmdpath.resolve()))
names=("Hips","Knee","Foot")
guard(set(motion.boneAnimation)==set(names) and
      all(len(motion.boneAnimation[n])==2 for n in names),
      "ROTATION_VMD_BONE_SET_OR_TWO_FRAME_CLOCK")
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.frame_set(0)
guard(scene.frame_current==0,"MMD_IMPORTER_FRAME_ORIGIN_MISMATCH")
ad=bpy.data.armatures.new("OriginalSyntheticRotationBones")
arm=bpy.data.objects.new("OriginalSyntheticRotationRig",ad)
scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
for n,h,t in (
    ("Hips",(0.,0.,.4),(0.,0.,.9)),
    ("Knee",(0.,0.,.0),(0.,0.,.4)),
    ("Foot",(0.,-.3,0.),(0.,-.1,0.))):
    bone=ad.edit_bones.new(n)
    bone.head=h
    bone.tail=t
bpy.ops.object.mode_set(mode="OBJECT")
for pb in arm.pose.bones:pb.rotation_mode="QUATERNION"
# Real ARMATURE skin as independently evaluated observer, not a humanoid model.
meshes=[]
for n in names:
    mesh=bpy.data.meshes.new(n+"_originalRotationQuad")
    mesh.from_pydata([(.0,.0,.0),(.20,.0,.02),(.18,.06,.02),(.02,.06,.0)],[],[(0,1,2,3)])
    obj=bpy.data.objects.new(n+"_rotation_skin",mesh)
    scene.collection.objects.link(obj)
    group=obj.vertex_groups.new(name=n)
    group.add([0,1,2,3],1.,"REPLACE")
    mod=obj.modifiers.new("ActualArmature","ARMATURE")
    mod.object=arm
    meshes.append(obj)
VMDImporter(str(vmdpath.resolve()),scale=1.,frame_margin=0).assign(arm)
guard(arm.animation_data is not None and arm.animation_data.action is not None,
      "UPSTREAM_IMPORTED_ROTATION_ANIMATION_ABSENT")
def state(f):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    quats={n:arm.pose.bones[n].rotation_quaternion.copy() for n in names}
    meshes_local={}
    for obj in meshes:
        e=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        m=e.to_mesh()
        try:
            meshes_local[obj.name]=[tuple(e.matrix_world@v.co) for v in m.vertices]
        finally:e.to_mesh_clear()
    return quats,meshes_local
q0,m0=state(0);q1,m1=state(1);q0r,m0r=state(0)
if fault=="static_pose":q1={n:q0[n].copy() for n in names}
def angular(a,b):
    return abs(a.rotation_difference(b).angle)
angles={n:angular(q0[n],q1[n]) for n in names}
sourceq=receipt["root_target_frame1_quat_xyzw"]
guard(len(sourceq)==4 and abs(sum(x*x for x in sourceq)-1)<1e-5,
      "NONUNIT_SOURCE_ROOT_QUATERNION")
source_angle=2*math.acos(min(1.,abs(float(sourceq[3]))))
# Source Z90/X90 gives 120deg. Verify native nontrivial actual pose, then
# separately report angle magnitude parity. Target rest axes are uncalibrated.
guard(abs(source_angle-2.0943951023931953)<1e-5,
      "WRONG_COMPOUND_SOURCE_ANGLE")
guard(angles["Hips"]>.35 and angles["Hips"]<3.1,
      "NATIVE_HIPS_ROTATION_NOT_OBSERVED")
rewind=max(angular(q0[n],q0r[n]) for n in names)
guard(rewind<1e-5,"BONE_ROTATION_REWIND")
skin_delta={}
for key in m0:
    skin_delta[key]=max(math.dist(a,b) for a,b in zip(m0[key],m1[key]))
guard(max(skin_delta.values())>.01,"ACTUAL_IMPORTED_SKIN_ROTATION_AND_TRANSLATION_FROZEN")
result={
  "schema":"scp.r009.original-synthetic-ordered-rotation-vmd-native-bpy.v1",
  "status":"PASS_SOURCE_AUTHORED_VMD_ROTATION_REACHED_ACTUAL_BPY_POSE",
  "source_vmd_sha256":sha,
  "source_first_target_rot_angle_rad":source_angle,
  "actual_blender_joint_angular_displacement_rad":angles,
  "evaluated_skin_vertex_max_delta_m":skin_delta,
  "native_rotation_rewind_error_rad":rewind,
  "upstream_mmd_tools":"f1d8a98db5e185cfa73c9b8a8a67fa42d9eb4b14",
  "blender":bpy.app.version_string,
  "source_axis_rest_to_target":"UNQUALIFIED",
  "physical_handedness":"UNKNOWN",
  "original_source_author":"SELF_AUTHORED_SYNTHETIC_DERIVATIVE_ONLY",
  "original_human_capture":"NOT_ADMITTED",
  "human_JCS_ROM":"UNKNOWN","measured_contact":"UNKNOWN",
  "private_R009":"HELD_NOT_ACCEPTED","CPE":"NOT_PROMOTED"
}
with out.open("x") as f:
    json.dump(result,f,sort_keys=True,indent=2);f.write("\n")
print("PASS_REAL_UPSTREAM_VMD_ORIGINAL_ROTATION_NATIVE_SYNTHETIC",json.dumps(result,sort_keys=True))
