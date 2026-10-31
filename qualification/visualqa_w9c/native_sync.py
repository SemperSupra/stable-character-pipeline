"""W9-C: a NEW synchronized 24-tick Blender camera witness, never edits original W7/W8 media.
Uses original native W7 source .blend + per-frame rig transforms, not regenerated H264.
"""
import argparse,hashlib,json,math
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
CAMERAS=(("OriginalFront",(0,-8.5,2.8),(0,0,1.15)),
         ("OriginalOblique",(7.5,-7,3.1),(0,0,1.15)))
ACTORS=("CobaltOriginal","MarigoldOriginal")
ROLES=(("Head",2.17),("Torso",1.50),("Pelvis",1.09))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def camera(name,eye,target):
 data=bpy.data.cameras.new(name+"_W9IndependentCameraData")
 ob=bpy.data.objects.new(name+"_W9IndependentCamera",data)
 bpy.context.scene.collection.objects.link(ob)
 ob.location=eye
 ob.rotation_euler=(Vector(target)-ob.location).to_track_quat("-Z","Y").to_euler()
 data.type="ORTHO";data.ortho_scale=5.75
 return ob
def execute(original,out):
 root=Path(original);out=Path(out);out.mkdir(parents=True,exist_ok=True)
 source_file=root/"source.json";blend=root/"original_source_grounded_24frame_native.blend"
 motion=json.loads((root/"source_motion_receipt.json").read_text())
 src=json.loads(source_file.read_text())
 if src.get("schema")!="scp.walk_w7a_original_approach.v1" or src.get("rights")!=RIGHTS or src.get("fps_num")!=12 or src.get("fps_den")!=1 or len(src.get("actors",[]))!=2:
  raise ValueError("W9C_ORIGINAL_SOURCE_UNADMITTED")
 if sha(source_file)!=motion.get("source_sha256") or sha(blend)!=motion.get("blend_sha256") or motion.get("rights")!=RIGHTS:
  raise ValueError("W9C_ORIGINAL_MODEL_SHA")
 bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
 scene=bpy.context.scene
 cams=[(name,camera(name,eye,target)) for name,eye,target in CAMERAS]
 outrows=[]
 for tick in range(24):
  scene.frame_set(tick)
  bpy.context.view_layer.update()
  for name,cam in cams:
   for actor in ACTORS:
    obj=bpy.data.objects.get(actor+"_Skeleton")
    if obj is None or obj.type!="ARMATURE":raise ValueError("W9C_MISSING_NATIVE_RIG")
    if obj.get("source_rights")!=RIGHTS:raise ValueError("W9C_RIG_RIGHTS")
    for part,height in ROLES:
     point=obj.matrix_world @ Vector((0,0,height))
     uv=world_to_camera_view(scene,cam,point)
     if not all(math.isfinite(float(v)) for v in (point.x,point.y,point.z,uv.x,uv.y,uv.z)):
      raise ValueError("W9C_NONFINITE_NATIVE_PROJECTION")
     if not (0<uv.x<1 and 0<uv.y<1 and uv.z>0):raise ValueError("W9C_OFFSCREEN_NATIVE_CORE")
     outrows.append({"camera":name,"tick":tick,"time_num":tick,"time_den":12,
       "actor":actor,"part":part,"xyz":[float(v) for v in point],
       "uv":[float(uv.x),float(uv.y)],"camera_depth_z":float(uv.z)})
 if len(outrows)!=24*2*2*3:raise ValueError("W9C_NATIVE_SAME_TICK_COVERAGE")
 if sha(blend)!=motion["blend_sha256"]:raise ValueError("W9C_ORIGINAL_MODEL_MUTATED")
 receipt={"schema":"scp.visualqa.w9c_native_same_tick.v1",
   "rights":RIGHTS,"source_sha256":sha(source_file),"native_blend_sha256":sha(blend),
   "original_source":src["profile"],"frames":24,"fps_num":12,"fps_den":1,
   "camera_count":2,"actor_count":2,"roles":["Head","Torso","Pelvis"],
   "same_tick_camera_pairs":True,"samples":outrows,
   "native_render_media":"NOT_RENDERED_NO_CLEAN_VIDEO_MUTATION",
   "original_W7_W8_camera_probe_skew":"RETAINED_AS_PRIOR_FIRST_FAILURE",
   "behavior_anatomy":"UNKNOWN_NOT_A_HUMAN_GAIT_OR_PIXEL_ORACLE"}
 (out/"native_same_tick.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
 print("W9C_NATIVE_SYNCHRONIZED_24_TICK_TWO_CAMERAS",len(outrows),sha(source_file))
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--artifact",required=True);p.add_argument("--out",required=True)
 x=p.parse_args();execute(x.artifact,x.out)
