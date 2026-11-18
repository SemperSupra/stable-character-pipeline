"""R081 actual Blender fine-motion and signed procedural tissue-morph attachment.
Operates only on the public fictional R078 MPFB scene. NOT accepted biomechanics.
"""
import argparse,hashlib,json,math,struct,sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).parent))
import fine_motion as m
REGIONS=("chest","abdomen","hip")
def fail(code):
 print("R081_NATIVE_RED",code,flush=True);raise RuntimeError(code)
def digest(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def skinhash(body):
 bpy.context.view_layer.update();e=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=e.to_mesh()
 try:
  h=hashlib.sha256()
  for v in mesh.vertices:h.update(struct.pack("<3f",v.co.x,v.co.y,v.co.z))
  return h.hexdigest(),len(mesh.vertices)
 finally:e.to_mesh_clear()
def add_tissue(body):
 if not body.data.shape_keys:body.shape_key_add(name="Basis",from_mix=False)
 base=body.data.shape_keys.key_blocks[0]
 coords=[v.co for v in body.data.vertices]
 mins=[min(v[k] for v in coords) for k in range(3)]
 maxs=[max(v[k] for v in coords) for k in range(3)]
 ext=[b-a for a,b in zip(mins,maxs)]
 if min(ext)<1e-5:fail("DEGENERATE_BODY_FOR_TISSUE")
 offsets=((0.,-.13,.78),(0.,-.13,.58),(0.,-.10,.43))
 shapes={}
 for region,(cx,cy,cz) in zip(REGIONS,offsets):
  masks=[];selected=0
  for xyz in coords:
   x=(xyz.x-mins[0])/ext[0]-.5;y=(xyz.y-mins[1])/ext[1]-.5;z=(xyz.z-mins[2])/ext[2]
   dx=(x-cx)/.34;dy=(y-cy)/.40;dz=(z-cz)/.14
   w=math.exp(-.5*(dx*dx+dy*dy+dz*dz))
   if w<.10:w=0.
   else:selected+=1
   masks.append(w)
  if selected<30:fail("TISSUE_MASK_TOO_SPARSE_"+region)
  kp=body.shape_key_add(name="R081_"+region+"_positive",from_mix=False)
  kn=body.shape_key_add(name="R081_"+region+"_negative",from_mix=False)
  for i,w in enumerate(masks):
   if w:
    b=base.data[i].co
    kp.data[i].co=(b.x,b.y-0.002*w,b.z)
    kn.data[i].co=(b.x,b.y+0.002*w,b.z)
  shapes[region]=(kp,kn,selected)
 return shapes
def choose_optional_bone(rig,stem,side):
 keys=(stem+"."+side,stem+"01."+side,stem+"02."+side)
 for n in keys:
  if n in rig.pose.bones:return n
 return None
def apply_pose(rig,frame,phase):
 p=m.pose(frame,phase)
 assignments={
  "upperleg01.L":p["upperleg_L"],"upperleg01.R":p["upperleg_R"],
  "lowerleg01.L":p["lowerleg_L"],"lowerleg01.R":p["lowerleg_R"]
 }
 missing_optional=[]
 for side in ("L","R"):
  foot=choose_optional_bone(rig,"foot",side)
  arm=choose_optional_bone(rig,"upperarm",side)
  if foot:assignments[foot]=p["heel_roll_"+side]
  else:missing_optional.append("foot."+side)
  if arm:assignments[arm]=p["arm_swing_"+side]
  else:missing_optional.append("upperarm."+side)
 for name,angle in assignments.items():
  if name not in rig.pose.bones:fail("MISSING_NATIVE_LEG_BONE_"+name)
  b=rig.pose.bones[name];b.rotation_mode="XYZ"
  b.rotation_euler=(angle,0.,0.)
  b.keyframe_insert(data_path="rotation_euler",frame=frame)
 return assignments,missing_optional
def build(a):
 sc=bpy.context.scene
 if sc.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0":fail("NOT_ADMITTED_FICTIONAL_BASELINE")
 if not m.validate():fail("FINITE_MOTION_CONTRACT")
 out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 receipt=[]
 for idx,name in enumerate(m.SOURCES):
  body=bpy.data.objects.get(name+"_MPFBBody")
  rig=bpy.data.objects.get(name+"_MPFBRig")
  root=bpy.data.objects.get(name+"_MotionRoot")
  if not body or not rig or not root:fail("ORIGINAL_MPF_PAIR_INCOMPLETE")
  if rig.type!="ARMATURE" or len(rig.data.bones)!=163:fail("NATIVE_RIG_CHANGED")
  if not any(mod.type=="ARMATURE" and mod.object==rig for mod in body.modifiers):fail("MISSING_REAL_SKIN_BINDING")
  rig.animation_data_clear();root.animation_data_clear()
  soft=add_tissue(body);series=m.tissue_series(m.PHASES[idx])
  driven=set();missing=set()
  for frame in range(m.FRAMES):
   positions=m.roots(frame)
   p=m.pose(frame,m.PHASES[idx])
   root.location=(positions[idx],p["sway_m"],p["bob_m"])
   root.keyframe_insert("location",frame=frame)
   on,not_found=apply_pose(rig,frame,m.PHASES[idx])
   driven.update(on);missing.update(not_found)
   for j,region in enumerate(REGIONS):
    value=series[frame][j];pos,neg,_=soft[region]
    pos.value=max(0.,value);neg.value=max(0.,-value)
    pos.keyframe_insert("value",frame=frame)
    neg.keyframe_insert("value",frame=frame)
  receipt.append({"name":name,"rig_bones":len(rig.data.bones),"driver_bones":sorted(driven),
                  "missing_optional_bones":sorted(missing),
                  "tissue_region_vertex_counts":{k:v[2] for k,v in soft.items()},
                  "tissue_keys_created":6,"tissue_calibration":"UNMEASURED_2MM_LOCAL_MORPH_ACTUATORS"})
 sc.frame_start=0;sc.frame_end=m.FRAMES-1;sc.render.fps=m.FPS
 sc["r081_tier"]="FICTIONAL_24FPS_PROVISIONAL_TISSUE"
 sc["r081_baseline_sha"]=a.baseline_sha
 sc.render.engine="BLENDER_WORKBENCH"
 sc.render.resolution_x=320;sc.render.resolution_y=180;sc.render.resolution_percentage=100
 sc.render.image_settings.file_format="PNG"
 sc.frame_set(0)
 destination=out/"aster-juniper-r081-fine-tissue.blend"
 bpy.ops.wm.save_as_mainfile(filepath=str(destination.resolve()))
 proof={"schema":"scp.r081.native-fine-motion.v1","scene_sha256":digest(destination),
        "original_baseline_sha256":a.baseline_sha,"fps":m.FPS,"frames":m.FRAMES,
        "actors":receipt,"source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
        "status":"PASS_NATIVE_FINE_TISSUE_ATTACH_NARROW_HOLD_PHYSICS",
        "gait_contact_accepted":False,"soft_tissue_physics_accepted":False,
        "source_identity_accepted":False,"photoreal_accepted":False,
        "mvp_accepted":False,"release_authorized":False}
 (out/"build.json").write_text(json.dumps(proof,sort_keys=True,indent=2)+"\n")
 print("R081_NATIVE_BUILD",json.dumps(proof,sort_keys=True),flush=True)
def verify(a):
 out=Path(a.out);path=Path(a.scene)
 if digest(path)!=a.scene_sha:fail("SAVED_SCENE_SHA_MISMATCH")
 sc=bpy.context.scene
 if sc.get("r081_tier")!="FICTIONAL_24FPS_PROVISIONAL_TISSUE":fail("NOT_FINE_TISSUE_SCENE")
 if (sc.frame_start,sc.frame_end,sc.render.fps)!=(0,143,24):fail("FRAME_CLOCK_CHANGED")
 build=json.loads((out/"build.json").read_text())
 if build["scene_sha256"]!=a.scene_sha:fail("RECEIPT_TO_SCENE_SHA_MISMATCH")
 observations=[]
 for frame in (0,47,95,143):
  sc.frame_set(frame)
  pair=[]
  for actor in build["actors"]:
   body=bpy.data.objects.get(actor["name"]+"_MPFBBody")
   rig=bpy.data.objects.get(actor["name"]+"_MPFBRig")
   root=bpy.data.objects.get(actor["name"]+"_MotionRoot")
   if not body or not rig or not root:fail("FRESH_REOPEN_ACTOR_LOST")
   keys=body.data.shape_keys
   if not keys:fail("SKIN_TISSUE_KEYS_LOST")
   for region in REGIONS:
    for sign in ("positive","negative"):
     if "R081_"+region+"_"+sign not in keys.key_blocks:fail("TISSUE_MORPH_LOST")
   sha,count=skinhash(body)
   if count<10000:fail("EVALUATED_BODY_EMPTY")
   pair.append({"name":actor["name"],"skin_sha256":sha,"root_x":round(root.location.x,6),
                "nonzero_tissue_controls":sum(1 for k in keys.key_blocks if k.name.startswith("R081_") and abs(k.value)>1e-7)})
  observations.append({"frame":frame,"actors":pair})
 if not observations[-1]["actors"][0]["root_x"]>observations[0]["actors"][0]["root_x"]+2:fail("ACTORS_NOT_APPROACHING")
 if any(observations[0]["actors"][i]["skin_sha256"]==observations[2]["actors"][i]["skin_sha256"] for i in (0,1)):fail("FRESH_REOPEN_SKIN_NOT_DEFORMING")
 if not any(o["actors"][i]["nonzero_tissue_controls"]>0 for o in observations[1:] for i in (0,1)):fail("TISSUE_CHANNELS_STATIC")
 sc.render.image_settings.file_format="PNG"
 stills=out/"stills";stills.mkdir(exist_ok=False)
 for frame in (0,71,143):
  sc.frame_set(frame);sc.render.filepath=str(stills/("frame_%03d.png"%frame));bpy.ops.render.render(write_still=True)
 if a.full_video:
  frames=out/"frames";frames.mkdir(exist_ok=False);sc.render.filepath=str(frames/"frame_")
  bpy.ops.render.render(animation=True)
 result={"schema":"scp.r081.native-fine-motion-reopen.v1","scene_sha256":a.scene_sha,
         "status":"PASS_24FPS_NATIVE_MOTION_TISSUE_NARROW_HOLD_CONTACT",
         "observations":observations,"rendered_animation":bool(a.full_video),
         "gait_contact_accepted":False,"physics_accepted":False,"identity_accepted":False,
         "mvp_accepted":False,"release_authorized":False}
 (out/"verify.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
 print("R081_NATIVE_VERIFY",json.dumps(result,sort_keys=True),flush=True)
def parse():
 p=argparse.ArgumentParser()
 p.add_argument("--stage",choices=("build","verify"),required=True)
 p.add_argument("--out",required=True);p.add_argument("--baseline-sha",default="")
 p.add_argument("--scene",default="");p.add_argument("--scene-sha",default="")
 p.add_argument("--full-video",action="store_true")
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])
if __name__=="__main__":
 try:
  a=parse()
  if a.stage=="build":build(a)
  else:verify(a)
 except (OSError,RuntimeError,ValueError,KeyError,TypeError) as e:
  print("R081_FAIL_CLOSED",repr(e),file=sys.stderr);sys.exit(12)
