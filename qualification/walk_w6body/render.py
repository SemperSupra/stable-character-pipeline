"""W6 source-original full-body geometric surrogate + two 24f native camera videos.

Overlay a plainly synthetic torso/head/arms onto independently qualified W5D
original 24-source-frame weighted foot/leg rigs. Neither anatomical naturalness
nor independent visual/person-model acceptance follows from surrogate pixels.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"walk_w16c5a"))
from w5d_grounded_native import animate
from native_sole import ACTORS,SOURCE
VIEWS=(("front",(0.,-8.5,2.8)),("oblique",(4.5,-8.5,3.2)))
COLORS=((.14,.38,.72,1.),(.84,.39,.16,1.))
def parent_part(arm,name,shape,loc,scale,col):
 if shape=="sphere":
  bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,location=(0,0,0))
 else:
  bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,0))
 obj=bpy.context.object;obj.name=name
 obj.parent=arm
 obj.matrix_parent_inverse.identity()
 obj.location=tuple(loc);obj.scale=tuple(scale);obj.color=tuple(col)
 obj["source_rights"]=SOURCE;obj["classification"]="NONANATOMIC_ABSTRACT_SURROGATE"
 return obj
def actor_body(name,profile,idx):
 arm=bpy.data.objects.get(name+"_Skeleton")
 if arm is None or arm.type!="ARMATURE":
  raise ValueError("W6_BODY_MISSING_W5D_SOURCE_RIG")
 color=COLORS[idx]
 parts=[]
 parts.append(parent_part(arm,name+"_Torso","cube",(0,0,1.38),(.57,.29,.62),color))
 parts.append(parent_part(arm,name+"_Neck","cube",(0,0,1.77),(.15,.14,.22),color))
 parts.append(parent_part(arm,name+"_Head","sphere",(0,0,1.97),(.19,.18,.23),color))
 for sign,label in ((-1,"Left"),(1,"Right")):
  parts.append(parent_part(arm,name+"_"+label+"_Arm","cube",(sign*.38,0,1.29),(.17,.20,.67),color))
  parts.append(parent_part(arm,name+"_"+label+"_Hand","sphere",(sign*.38,0,.92),(.095,.095,.13),color))
 if len(parts)!=7:
  raise ValueError("W6_BODY_INCOMPLETE_SURROGATE")
 return parts
def camera_for(name,pos):
 camdata=bpy.data.cameras.new("W6_"+name+"_CameraData")
 camdata.type="ORTHO";camdata.ortho_scale=5.5
 cam=bpy.data.objects.new("W6_"+name+"_Camera",camdata)
 bpy.context.scene.collection.objects.link(cam)
 cam.location=pos
 vec=Vector((0,0,1.05))-cam.location
 cam.rotation_euler=vec.to_track_quat("-Z","Y").to_euler()
 return cam
def source_project(scene,cam,profile):
 samples=[]
 for frame in (0,12,23):
  scene.frame_set(frame)
  entry={"frame":frame,"actors":[]}
  for name,x in ACTORS:
   actor=bpy.data.objects.get(name+"_Skeleton")
   pts={}
   for label,coords in (("head_top",(0,0,2.20)),("foot_level",(0,0,0.))):
    world=actor.matrix_world@Vector(coords)
    q=world_to_camera_view(scene,cam,world)
    if not(0<q.x<1 and 0<q.y<1 and q.z>0):
     raise ValueError("W6_BODY_CAMERA_OFFSCREEN_"+name+"_"+label)
    pts[label]=[float(q.x),float(q.y),float(q.z)]
   height=pts["head_top"][1]-pts["foot_level"][1]
   if height<.24 or height>.88:
    raise ValueError("W6_BODY_CAMERA_HUMANOID_BBOX_OUT_OF_RANGE")
   entry["actors"].append({"name":name,"head":pts["head_top"],"sole":pts["foot_level"],
      "source_projected_height_fraction":height})
  samples.append(entry)
 return samples
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--profile",choices=("forward","outward"),required=True)
 p.add_argument("--source",required=True);p.add_argument("--out",required=True)
 opts=p.parse_args()
 out=Path(opts.out);out.mkdir(parents=True,exist_ok=True)
 src_raw=Path(opts.source).read_bytes()
 source=json.loads(src_raw)
 if source.get("rights")!=SOURCE or source.get("profile")!=opts.profile or source.get("schema")!="scp.walk_c4_original_ground_feasibility.v1":
  raise ValueError("W6_BODY_UNADMITTED_C4_SOURCE")
 base=animate(source,opts.profile,out)
 if base.get("status")!="PASS_ORIGINAL_SOURCE_24FRAME_WEIGHTED_SKIN_FOOT_OBSERVED_ONLY":
  raise ValueError("W6_BODY_W5D_BASE_FAILURE")
 scene=bpy.context.scene
 for i,(name,x) in enumerate(ACTORS):
  actor_body(name,opts.profile,i)
 floor=parent_part(None,"W6_Ground","cube",(0,0,-.035),(10.,10.,.07),(.31,.38,.30,1.))
 floor["classification"]="ORIGINAL_SYNTHETIC_GROUND_Z0"
 scene.render.engine="BLENDER_WORKBENCH"
 scene.display.shading.color_type="OBJECT"
 scene.render.resolution_x=400;scene.render.resolution_y=240
 scene.render.resolution_percentage=100
 scene.render.film_transparent=False
 scene.render.image_settings.file_format="FFMPEG"
 scene.render.ffmpeg.format="MPEG4";scene.render.ffmpeg.codec="H264"
 scene.render.ffmpeg.constant_rate_factor="HIGH"
 scene.frame_start=0;scene.frame_end=23;scene.render.fps=12
 cameras=[];projections={}
 for name,loc in VIEWS:
  cam=camera_for(name,loc)
  scene.camera=cam
  projections[name]=source_project(scene,cam,opts.profile)
  cameras.append((name,cam))
 scene.frame_set(0)
 blend=out/"original_two_actor_fullbody_surrogate.blend"
 bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
 glb=out/"original_two_actor_fullbody_surrogate.glb"
 bpy.ops.export_scene.gltf(filepath=str(glb.resolve()),export_format="GLB",export_animations=True)
 outputs={}
 for name,cam in cameras:
  scene.camera=cam
  scene.render.filepath=str((out/("original_"+name+"_surrogate.mp4")).resolve())
  bpy.ops.render.render(animation=True)
  video=out/("original_"+name+"_surrogate.mp4")
  if not video.exists() or video.stat().st_size<2000:
   raise ValueError("W6_BODY_NATIVE_VIDEO_MISSING")
  outputs[name]={"sha256":hashlib.sha256(video.read_bytes()).hexdigest(),"bytes":video.stat().st_size}
 receipt={"schema":"scp.walk_w6_original_fullbody_multiview.v1",
  "status":"PASS_ORIGINAL_FULL_BODY_SURROGATE_AND_NATIVE_MULTICAMERA_RENDER_ONLY",
  "source_rights":SOURCE,"source_sha256":hashlib.sha256(src_raw).hexdigest(),
  "profile":opts.profile,"source_gait_receipt_sha256":hashlib.sha256((out/"source_motion_receipt.json").read_bytes()).hexdigest(),
  "source_frame_count":24,"render_video_frames_per_view":24,"fps":12,
  "abstract_body_parts_per_actor":7,"actors":2,"views":outputs,
  "source_projection":projections,
  "blend_sha256":hashlib.sha256(blend.read_bytes()).hexdigest(),
  "glb_sha256":hashlib.sha256(glb.read_bytes()).hexdigest(),
  "full_body_geometry":"ORIGINAL_ABSTRACT_INCOMPLETE_ANATOMICAL_DETAILS",
  "true_skin_anatomy":"UNKNOWN_NOT_A_PERSON_MODEL",
  "original_visualqa_l1":"RED_PREVIOUS_SOURCED_VIDEO_NOT_REEVALUATED",
  "human_rom":"UNKNOWN_NO_SPECIES_JOINT_AXES_OR_LOADING",
  "scope":"CAMERA_AND_DECODED_VISIBILITY_OBSERVATION_NOT_HUMAN_OR_PRIVATE_R009_ACCEPTANCE"}
 (out/"multiview_render_receipt.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
 print("W6_ORIGINAL_MULTIVIEW_FULLBODY_SURROGATE_RENDER_PASS",opts.profile,outputs)
if __name__=="__main__":main()
