#!/usr/bin/env python3
"""Unmodified upstream MMD Tools VMDImporter.assign -> actual Blender bpy pose.
Original BVH fixture only; target axis/physical semantics remain unadmitted.
"""
import bpy,sys,json,hashlib,pathlib,zipfile,tempfile,math
if "--" not in sys.argv:raise SystemExit("need --")
args=sys.argv[sys.argv.index("--")+1:]
if len(args)!=4:raise SystemExit("expected VMD UPSTREAM SOURCE_RECEIPT OUT")
file,root,receipt,out=map(pathlib.Path,args)
raw=file.read_bytes();r=json.loads(receipt.read_text())
if hashlib.sha256(raw).hexdigest()!=r["vmd_sha256"] or r["source_frame_1"]!="DROPPED_30FPS_RESAMPLE":
    raise RuntimeError("BVH_VMD_SOURCE_CUSTODY_MISMATCH")
if r["private_R009"]!="HELD_NOT_ACCEPTED":raise RuntimeError("FALSE_PRODUCT_PROMOTION")
wheel=root/"mmd_tools"/"wheels"/"opencc_python_reimplemented-0.1.7-py2.py3-none-any.whl"
if not wheel.is_file():raise RuntimeError("PINNED_UNMODIFIED_OPENCC_REQUIRED")
tmp=pathlib.Path(tempfile.mkdtemp(prefix="scp-opencc-"))
with zipfile.ZipFile(wheel) as z:
    members=z.infolist()
    if len(members)>3000:raise RuntimeError("UNBOUNDED_UPSTREAM_WHEEL")
    for m in members:
        p=pathlib.PurePosixPath(m.filename)
        if p.is_absolute() or ".." in p.parts or m.file_size>10000000:raise RuntimeError("BAD_UPSTREAM_WHEEL_PATH")
    z.extractall(tmp)
sys.path.insert(0,str(tmp));sys.path.insert(0,str(root.resolve()))
from mmd_tools.core.vmd.importer import VMDImporter
from mmd_tools.core import vmd
motion=vmd.File();motion.load(filepath=str(file.resolve()))
names=("Hips","Knee","Foot")
if set(motion.boneAnimation)!=set(names) or any(len(motion.boneAnimation[n])!=2 for n in names):
    raise RuntimeError("UPSTREAM_VMD_NAMES_OR_CLOCK_DISAGREE")
bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
armdata=bpy.data.armatures.new("OriginalBVH3");arm=bpy.data.objects.new("OriginalBVH3",armdata)
bpy.context.scene.collection.objects.link(arm);bpy.context.view_layer.objects.active=arm;arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
for name,head,tail in [("Hips",(0,0,.4),(0,0,.8)),("Knee",(0,0,0),(0,0,.3)),("Foot",(0,-.4,0),(0,-.2,0))]:
    b=armdata.edit_bones.new(name);b.head=head;b.tail=tail
bpy.ops.object.mode_set(mode="OBJECT")
for pb in arm.pose.bones:pb.rotation_mode="QUATERNION"
meshes=[]
for name in names:
    b=bpy.data.objects.new(name+"_mesh",bpy.data.meshes.new(name+"_quad"))
    b.data.from_pydata([(-.03,0,0),(.03,0,0),(.03,.06,0),(-.03,.06,0)],[],[(0,1,2,3)])
    bpy.context.scene.collection.objects.link(b)
    group=b.vertex_groups.new(name=name);group.add([0,1,2,3],1.0,"REPLACE")
    mod=b.modifiers.new("ActualArmatureModifier","ARMATURE");mod.object=arm;meshes.append(b)
VMDImporter(str(file.resolve()),scale=1.0,frame_margin=0).assign(arm)
if not arm.animation_data or not arm.animation_data.action:raise RuntimeError("ACTUAL_BPY_ACTION_MISSING")
def sample(frame):
    bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
    pose={n:tuple(arm.pose.bones[n].location) for n in names}
    evaluated={}
    for ob in meshes:
        eo=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=eo.to_mesh()
        try:evaluated[ob.name]=tuple(sum(v.co[k] for v in me.vertices)/len(me.vertices) for k in range(3))
        finally:eo.to_mesh_clear()
    return pose,evaluated
p0,m0=sample(0);p1,m1=sample(1);p0b,m0b=sample(0)
deltas={n:math.dist(p0[n],p1[n]) for n in names}
skin={n:math.dist(m0[n],m1[n]) for n in m0}
print("NATIVE_BVH_VMD_BPY_POSE_AND_SKIN_DIAGNOSTIC",json.dumps({"joint_deltas":deltas,"skin_deltas":skin,"pose_frame0":p0,"pose_frame1":p1,"source_vmd_sha256":hashlib.sha256(raw).hexdigest()},sort_keys=True),flush=True)
if any(d<.2 or d>2 for d in deltas.values()):raise RuntimeError("SOURCE_VMD_BPY_MOTION_DISAGREES")
if any(d<.2 for d in skin.values()):raise RuntimeError("ACTUAL_BPY_SKIN_FROZEN")
if max(math.dist(p0[n],p0b[n]) for n in names)>1e-6:raise RuntimeError("POSE_REWIND_FAILED")
result={"schema":"scp.r009.original-bvh-vmd-native-bpy.v1",
"status":"PASS_ACTUAL_BPY_MMD_TOOLS_AUTHORED_BVH_CROSSWALK_ONLY",
"vmd_sha256":hashlib.sha256(raw).hexdigest(),
"mmd_tools_commit":"f1d8a98db5e185cfa73c9b8a8a67fa42d9eb4b14",
"blender":bpy.app.version_string,"frames":[0,1],
"bpy_bone_displacement":deltas,"actual_skinned_mesh_displacement":skin,
"lost_source_frame":"1_of_3_dropped_explicitly","axis_handness_physical_mapping":"UNQUALIFIED",
"actual_human_capture":"NOT_ADMITTED","human_JCS_ROM":"UNKNOWN","private_R009":"HELD_NOT_ACCEPTED"}
with out.open("x") as f:json.dump(result,f,sort_keys=True,indent=2);f.write("\n")
print(json.dumps(result,sort_keys=True))
