"""R078 real official MPFB synthetic Aster/Juniper pair; no protected originals."""
import argparse,hashlib,importlib,json,math,os,struct,sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import contract as c
def fail(code):
 print("R078_NATIVE_RED",code,flush=True);raise RuntimeError(code)
def digest(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for x in iter(lambda:f.read(1<<20),b""):h.update(x)
 return h.hexdigest()
def evaluated_local(obj):
 bpy.context.view_layer.update()
 e=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
 mesh=e.to_mesh()
 try:
  h=hashlib.sha256()
  for v in mesh.vertices:
   h.update(struct.pack("<3f",v.co.x,v.co.y,v.co.z))
  return h.hexdigest(),len(mesh.vertices)
 finally:e.to_mesh_clear()
def body_shape_metrics(body,rig):
 # Diagnostic metrics only; rig-local bone origins are not validated anatomical joint centres.
 bpy.context.view_layer.update()
 e=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=e.to_mesh()
 try:
  coords=[(v.co.x,v.co.y,v.co.z) for v in mesh.vertices]
  if not coords:fail("EMPTY_EVALUATED_HUMAN")
  ext=[max(p[k] for p in coords)-min(p[k] for p in coords) for k in range(3)]
  if not all(math.isfinite(v) and v>1e-6 for v in ext):fail("INVALID_BODY_EXTENT")
  bones=rig.data.bones
  leg={}
  for side in ("L","R"):
   for segment,bone in (("upper","upperleg01."+side),("lower","lowerleg01."+side)):
    if bone not in bones:fail("MISSING_CALIBRATION_RIG_BONE_"+bone)
    value=bones[bone].length/ext[2]
    if not math.isfinite(value) or value<=0:fail("INVALID_SEGMENT_RATIO")
    leg[segment+"_"+side+"_over_height"]=round(value,8)
  return {"bbox_x_over_height":round(ext[0]/ext[2],8),
          "bbox_y_over_height":round(ext[1]/ext[2],8),
          "leg_segments":leg,"measured_from":"EVALUATED_SAVED_MPF_BODY_AND_NATIVE_REST_RIG",
          "anatomical_landmark_centres_accepted":False}
 finally:e.to_mesh_clear()
\ndef services():
 import addon_utils
 mod="bl_ext.user_default.mpfb"
 if not addon_utils.check(mod)[1]:addon_utils.enable(mod,default_set=False,persistent=False)
 if not addon_utils.check(mod)[1]:fail("PINNED_MPF_EXTENSION_UNAVAILABLE")
 hs=importlib.import_module(mod+".services.humanservice").HumanService
 ts=importlib.import_module(mod+".services.targetservice").TargetService
 props=importlib.import_module(mod+".entities.objectproperties").HumanObjectProperties
 return hs,ts,props
def material(name,color):
 m=bpy.data.materials.new(name)
 m.diffuse_color=(*color,1.0)
 m.use_nodes=True
 p=m.node_tree.nodes.get("Principled BSDF")
 if p:
  p.inputs["Base Color"].default_value=(*color,1.)
  p.inputs["Roughness"].default_value=.74
 return m
def top_root(name,body,rig):
 # Preserve upstream parent-child hierarchy; do not parent an object twice.
 root=bpy.data.objects.new(name+"_MotionRoot",None)
 bpy.context.collection.objects.link(root)
 if body.parent is None:body.parent=root
 if rig.parent is None:rig.parent=root
 if body.parent not in (root,rig):fail("UNKNOWN_MPF_BODY_PARENT")
 if rig.parent!=root:fail("UNKNOWN_MPF_RIG_PARENT")
 return root
def setpose(rig,frame,phase):
 t=frame/c.FPS;osc=2*math.pi*1.25*t+phase
 names=[("upperleg01.L",.32,0),("upperleg01.R",-.32,0),
        ("lowerleg01.L",.17,0),("lowerleg01.R",.17,math.pi)]
 for name,amp,offset in names:
  if name not in rig.pose.bones:fail("MISSING_CANONICAL_LEG_BONE_"+name)
  bone=rig.pose.bones[name]
  bone.rotation_mode="XYZ"
  # Original provisional authored gait; NOT real physical contact.
  angle=(max(0,math.sin(osc+offset))*.4+.12) if name.startswith("lowerleg") else amp*math.sin(osc+offset)
  bone.rotation_euler=(angle,0,0)
  bone.keyframe_insert("rotation_euler",frame=frame)
def build(args):
 c.validate_profiles()
 if not (Path(args.source)/"src/mpfb/data/3dobjs/base.obj").is_file():fail("PINNED_CORE_MISSING")
 bpy.ops.wm.read_factory_settings(use_empty=True)
 hs,ts,props=services()
 details=[]
 roots=[]
 for i,p in enumerate(c.PROFILES):
  body=hs.create_human()
  if body is None or body.type!="MESH":fail("MPF_BODY_CREATION_FAILED")
  rig=hs.add_builtin_rig(body,"default",import_weights=True)
  if rig is None or rig.type!="ARMATURE":fail("MPF_RIG_CREATION_FAILED")
  for key in c.PHENOTYPE_KEYS:props.set_value(key,p[key],entity_reference=body)
  ts.reapply_macro_details(body)
  hs.refit(body)
  body.name=p["name"]+"_MPFBBody"
  rig.name=p["name"]+"_MPFBRig"
  if len(rig.data.bones)<100 or len(body.data.vertices)<10000:fail("LOW_FIDELITY_OR_EMPTY_MPF_RIG")
  if not any(m.type=="ARMATURE" and m.object==rig for m in body.modifiers):fail("SKIN_NOT_BOUND_TO_OFFICIAL_MPF_RIG")
  body.data.materials.clear()
  body.data.materials.append(material(p["name"]+"_ProceduralSkin",p["skin_color"]))
  root=top_root(p["name"],body,rig)
  for frame in range(c.FRAMES):
   setpose(rig,frame,p["phase"])
   x=c.source_centers(frame)[i]
   root.location=(x,0,0)
   root.keyframe_insert("location",frame=frame)
  bpy.context.scene.frame_set(0)
  rest,count=evaluated_local(body)
  bpy.context.scene.frame_set(35)
  mid,count2=evaluated_local(body)
  if rest==mid or count!=count2:fail("ACTUAL_MPF_BODY_SKIN_NOT_MOVING")
  details.append({"name":p["name"],"body":body.name,"rig":rig.name,"root":root.name,
   "profile":{k:p[k] for k in c.PHENOTYPE_KEYS},
   "native_body_shape_metrics":body_shape_metrics(body,rig),
   "bones":len(rig.data.bones),"body_vertices":len(body.data.vertices),
   "evaluated_vertices":count,"rest_pose_sha256":rest,"mid_pose_sha256":mid,
   "body_source":"PINNED_OFFICIAL_MPF_HUMANSERVICE",
   "materials":"ORIGINAL_PROCEDURAL_NO_EXTERNAL_TEXTURE"})
  roots.append(root)
 scene=bpy.context.scene
 scene.frame_start=0;scene.frame_end=71;scene.render.fps=12
 scene.render.engine="BLENDER_WORKBENCH"
 scene.render.resolution_x=320;scene.render.resolution_y=180
 scene.render.resolution_percentage=100
 scene.render.image_settings.file_format="PNG"
 camera=bpy.data.cameras.new("R078_AsterJuniper_Camera")
 cam=bpy.data.objects.new(camera.name,camera);bpy.context.collection.objects.link(cam)
 cam.location=(0,-11,2.75)
 cam.rotation_euler=(Vector((0,0,1.05))-cam.location).to_track_quat("-Z","Y").to_euler()
 camera.type="ORTHO";camera.ortho_scale=8.5;scene.camera=cam
 bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,-.02))
 ground=bpy.context.object
 ground.name="R078_Original_FlatParkProxy"
 ground.dimensions=(12,3,.04)
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if abs(max((ground.matrix_world@Vector(v)).z for v in ground.bound_box))>1e-5:fail("GROUND_NOT_AT_ZERO")
 scene.frame_set(0)
 out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
 scene["r078_source"]="ORIGINAL_FICTIONAL_MPFBCORE_CC0"
 scene["r078_upstream"]=c.UPSTREAM
 saved=out/"aster-juniper-official-mpfb.blend"
 bpy.ops.wm.save_as_mainfile(filepath=str(saved.resolve()))
 receipt={"schema":c.SCHEMA,"status":"HOLD_NATIVE_CONTACT_AND_VISUAL","source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
  "mpfb_upstream_commit":c.UPSTREAM,"original_aster_juniper_source_reference_sha256":c.SOURCE_ORIGINAL,
  "fps":12,"frames":72,"actors":details,"blender_version":bpy.app.version_string,
  "blend_sha256":digest(saved),"photoreal_accepted":False,"gait_accepted":False,
  "real_identity_accepted":False,"mvp_accepted":False,"release_authorized":False,
  "asset_rights_scope":"official MPFB CC0 core only; no external hair/clothes/textures",
  "operator_note":"Female phenotype and broader macro sliders remain FICTIONAL source-safe hypotheses; body extents and bone lengths are native diagnostics, not original-character matching or anatomical centres."}
 c.validate_receipt(receipt)
 (out/"build.json").write_text(json.dumps(receipt,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("R078_MPF_PAIR_BUILD",json.dumps({"sha":receipt["blend_sha256"],"actors":details},sort_keys=True),flush=True)
def verify(args):
 path=Path(args.saved)
 if not path.is_file() or digest(path)!=args.sha:fail("SAVED_SCENE_SHA_MISMATCH")
 # New Blender process opens the scene BEFORE script invocation.
 sc=bpy.context.scene
 if sc.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0" or sc.get("r078_upstream")!=c.UPSTREAM:fail("SOURCE_CLASS_AND_PIN_CHANGED")
 if (sc.frame_start,sc.frame_end,sc.render.fps)!=(0,71,12):fail("SOURCE_TIMEBASE_MISMATCH")
 with open(Path(args.out)/"build.json",encoding="utf8") as f:r=json.load(f)
 c.validate_receipt(r)
 if r["blend_sha256"]!=args.sha:fail("SOURCE_RECEIPT_MISMATCH")
 observations=[]
 for frame in (0,35,71):
  sc.frame_set(frame)
  actors=[]
  for row in r["actors"]:
   body=bpy.data.objects.get(row["body"]);rig=bpy.data.objects.get(row["rig"]);root=bpy.data.objects.get(row["root"])
   if body is None or rig is None or root is None:fail("SOURCE_ACTOR_LOST")
   if not any(m.type=="ARMATURE" and m.object==rig for m in body.modifiers):fail("ACTUAL_RIG_BINDING_LOST")
   h,v=evaluated_local(body)
   if v!=row["evaluated_vertices"]:fail("ACTOR_VERTEX_COUNT_DRIFT")
   actors.append({"name":row["name"],"body_local_sha":h,"root_x_m":round(root.location.x,6)})
  separation=abs(actors[0]["root_x_m"]-actors[1]["root_x_m"])
  observations.append({"frame":frame,"actors":actors,"root_separation_m":round(separation,6)})
 if not observations[-1]["root_separation_m"]<observations[0]["root_separation_m"]-1:fail("REAL_RIGS_DO_NOT_APPROACH")
 for i,row in enumerate(r["actors"]):
  if observations[0]["actors"][i]["body_local_sha"]==observations[1]["actors"][i]["body_local_sha"]:fail("REAL_SKIN_NOT_DEFORMING")
 out=Path(args.out)
 frames=out/"stills";frames.mkdir(exist_ok=False)
 sc.render.image_settings.file_format="PNG"
 for frame in (0,35,71):
  sc.frame_set(frame);sc.render.filepath=str(frames/("frame_%03d.png"%frame))
  bpy.ops.render.render(write_still=True)
 result={"schema":"scp.r078.mpfb-pair-fresh-reopen.v1","status":"PASS_NATIVE_SKIN_RIG_SOURCE_NARROW_HOLD_GAIT",
  "scene_sha256":args.sha,"observations":observations,
  "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
  "mvp_accepted":False,"photoreal_accepted":False,"gait_contact_accepted":False,
  "release_authorized":False}
 (out/"verify.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
 print("R078_MPF_PAIR_REOPEN",json.dumps(result,sort_keys=True),flush=True)
def parse():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("--stage",choices=("build","verify"),required=True)
 p.add_argument("--source",default="")
 p.add_argument("--out",required=True)
 p.add_argument("--saved",default="")
 p.add_argument("--sha",default="")
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])
if __name__=="__main__":
 try:
  a=parse()
  if a.stage=="build":build(a)
  else:verify(a)
 except (RuntimeError,ValueError,OSError,KeyError,TypeError) as err:
  print("R078_FAIL",repr(err),file=sys.stderr)
  sys.exit(12)
