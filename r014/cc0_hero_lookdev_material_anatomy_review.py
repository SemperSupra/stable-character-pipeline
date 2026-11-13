"""Original CC0/MPFB full-human visual-material audit from cold-imported GLB.

True Blender Cycles evidence of full body, facial close-up, hand region, and
feet, with real image/material-node custody. Visual rating remains HUMAN_HOLD;
this probe never infers complete external anatomy or photorealism from meshes.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

ap=argparse.ArgumentParser()
ap.add_argument("--sex",choices=("female","male"),required=True)
ap.add_argument("--source",type=Path,required=True)
ap.add_argument("--out",type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
a.out.mkdir(parents=True,exist_ok=True)
assert Path(bpy.data.filepath).resolve()==a.source.resolve()
body=bpy.data.objects["R014_"+a.sex+"_textured_body"]
rig=bpy.data.objects["R014_"+a.sex+"_textured_rig"]
assert body.type=="MESH" and rig.type=="ARMATURE"
assert len(rig.data.bones)==163 and len(body.data.vertices)>=13000,"cold source import shape/body missing"
assert any(m.type=="ARMATURE" and m.object==rig for m in body.modifiers)
assert len(body.data.shape_keys.key_blocks)==(30 if a.sex=="female" else 20)
assert len(body.data.uv_layers)>0,"cold GLB lost body UV map"
meshes=sorted([o for o in bpy.data.objects if o.type=="MESH"],key=lambda x:x.name)
assert len(meshes)>=7
# Critical observed negative: prior first multiview images had a giant white
# default Cube occluding source legs; the GLB truly has seven character meshes,
# but cold-import Blender scene retained unrelated Cube/Icosphere fixture.
# This renderer explicitly excludes ONLY these independent original primitives
# and logs the exclusion. The source GLB, body, hair and native rig are untouched.
nonactor=[o for o in meshes if not o.name.startswith("R014_"+a.sex+"_textured_body")]
assert set(o.name for o in nonactor).issubset({"Cube","Icosphere"}), "unexpected unrelated scene mesh requires manual review"
for o in nonactor:o.hide_render=True
scene=bpy.context.scene
actions=list(bpy.data.actions)
assert actions,"real cold import is missing rig animation"
scene.frame_set(2)
bpy.context.view_layer.update()
deps=bpy.context.evaluated_depsgraph_get()
mesh=body.evaluated_get(deps).to_mesh()
try:
 xyz=np.asarray([list(body.matrix_world@v.co) for v in mesh.vertices],dtype=float)
 faces=[list(p.vertices) for p in mesh.polygons]
finally:
 body.evaluated_get(deps).to_mesh_clear()
assert np.isfinite(xyz).all() and xyz.shape==(len(body.data.vertices),3)
lower=np.min(xyz,axis=0);upper=np.max(xyz,axis=0)
extent=upper-lower
assert np.min(extent)>.01 and np.max(extent)<20
center=(lower+upper)/2.0
tri_count=sum(len(f)-2 for f in faces)
assert tri_count>=20000

def sha(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for c in iter(lambda:f.read(1048576),b""):h.update(c)
 return h.hexdigest()

def scan_material(mat):
 nodes=list(mat.node_tree.nodes) if mat and mat.use_nodes else []
 BSDF=[n for n in nodes if n.type=="BSDF_PRINCIPLED"]
 images=[]
 for n in nodes:
  if n.type=="TEX_IMAGE":
   im=n.image
   images.append({
    "image":im.name if im else "MISSING_IMAGE",
    "pixels":list(im.size) if im else [],
    "has_packed_source":bool(im and im.packed_file),
    "filepath_hint":Path(im.filepath).name if im else "",
    "colorspace":im.colorspace_settings.name if im else None
   })
 return {"name":mat.name if mat else "UNASSIGNED",
   "node_based":bool(mat and mat.use_nodes),
   "principled_bsdf_count":len(BSDF),
   "image_texture_nodes":images,
   "normal_nodes":sum(n.type=="NORMAL_MAP" for n in nodes),
   "bump_nodes":sum(n.type=="BUMP" for n in nodes),
   "displacement_nodes":sum(n.type=="DISPLACEMENT" for n in nodes),
   "principled_subsurface_weights":[float(n.inputs["Subsurface Weight"].default_value)
                                    for n in BSDF if n.inputs.get("Subsurface Weight")],
   "completeness":"NUMERIC_NODE_CENSUS_ONLY_NOT_LOOKDEV_ACCEPTANCE"}
materials={}
for obj in meshes:
 materials[obj.name]={
  "vertices":len(obj.data.vertices),
  "polygons":len(obj.data.polygons),
  "uv_sets":len(obj.data.uv_layers),
  "materials":[scan_material(m) for m in obj.data.materials],
 }
body_mat=materials[body.name]["materials"]
eyes=[name for name in materials if "eye" in name.lower()]
hair=[name for name in materials if any(k in name.lower() for k in ("hair","brow","lash"))]
teeth=[name for name in materials if "teeth" in name.lower() or "tooth" in name.lower()]
tongue=[name for name in materials if "tongue" in name.lower()]
# A named accessory/skin material proves only presence; textured vs anatomical
# correctness, uv seam, hair shading and 4K quality are separate review gates.
scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=12
scene.render.threads_mode="FIXED"
scene.render.threads=4
scene.render.resolution_x=576
scene.render.resolution_y=704
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
world=bpy.data.worlds.new("R014_HeroReviewWorld")
world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.65
scene.world=world
lightdata=bpy.data.lights.new("R014_HeroReviewSoftbox","AREA")
light=bpy.data.objects.new("R014_HeroReviewSoftbox",lightdata)
bpy.context.collection.objects.link(light)
lightdata.energy=600;lightdata.size=max(2.,float(extent[2])*.65)
camera_data=bpy.data.cameras.new("R014_HeroReviewCamera")
camera=bpy.data.objects.new("R014_HeroReviewCamera",camera_data)
bpy.context.collection.objects.link(camera)
scene.camera=camera;camera_data.type="ORTHO"
def render_view(label,focus,view,scale):
 f=Vector(tuple(float(x) for x in focus))
 direction=Vector(tuple(float(x) for x in view))
 camera.location=f+direction
 camera.rotation_euler=(f-camera.location).to_track_quat("-Z","Y").to_euler()
 camera_data.ortho_scale=scale
 light.location=f+Vector((1.,-2.,1.5))
 scene.render.filepath=str(a.out/(a.sex+"_"+label+".png"))
 bpy.ops.render.render(write_still=True)
 path=Path(scene.render.filepath)
 assert path.stat().st_size>5000
 return {"name":path.name,"sha256":sha(path),"pixels":[576,704],
         "view":"source geometry crop/review, no independently judged photorealism"}
views=[]
height=float(extent[2]);wide=float(extent[0])
views.append(render_view("whole_body_front",center,(.05,-max(3.,height*2.),.05),max(2.0,height*1.22)))
views.append(render_view("face_close",(
 center[0],center[1],float(upper[2]-.13*height)),(.05,-max(1.2,height),.15),
 max(.55,height*.36)))
views.append(render_view("upper_limb_close",(
 center[0]+.32*wide,center[1],float(lower[2]+.53*height)),(.4,-max(1.4,height),.3),
 max(.65,height*.45)))
views.append(render_view("foot_close",(
 center[0],center[1],float(lower[2]+.11*height)),(.3,-max(1.5,height),.15),
 max(.60,height*.32)))

receipt={
 "schema":"r014.cc0.hero_lookdev_material_anatomy_visibility.v1",
 "sex":a.sex,
 "source_type":"actual CC0/MPFB cold-reimported native full adult GLB",
 "original_source_sha256":sha(a.source),
 "structural_status":"PASS_TRUE_COLD_IMPORTED_SKIN_MORPH_SURFACE_CENSUS",
 "aesthetic_status":"HOLD_HUMAN_INDEPENDENT_PHOTOREAL_AND_COMPLETE_EXTERNAL_ANATOMY_REVIEW",
 "mhr_compatibility":"NOT_ESTABLISHED; separate candidate skeleton",
 "body_vertices":len(body.data.vertices),"rig_bones":len(rig.data.bones),
 "body_morph_keys":len(body.data.shape_keys.key_blocks),
 "body_uv_sets":len(body.data.uv_layers),
 "body_triangle_fans":tri_count,
 "non_character_default_blender_primitives_excluded_from_review_images":[o.name for o in nonactor],
 "non_character_render_exclusion_must_not_change_original_asset":True,
 "body_world_bbox":{ "lower":lower.tolist(),"upper":upper.tolist(),"extent":extent.tolist()},
 "cold_import_actions":[{"name":x.name,"frames":list(x.frame_range)} for x in actions],
 "observed_named_accessories":{
   "eye_named_meshes":eyes,"hair_or_brow_named_meshes":hair,
   "teeth_named_meshes":teeth,"tongue_named_meshes":tongue},
 "actual_material_and_texture_nodes":materials,
 "technical_multi_view_pngs":views,
 "source_rights":"original MPFB/MakeHuman source synthetic CC0 core; third-party bundled materials require individual custody review",
 "not_proven":[
  "Anatomical region completeness or external genital geometry",
  "Professional skin pore normal/displacement/SSS/eye cornea/hair strand quality",
  "Body shader currently 0 SSS weights in six original body material slots; no photoreal skin claim",
  "Hair, eyes, teeth and tongue rigging/physics/collision with motion",
  "Microgeometry UV/LOD comparisons, physical skin reflectance or human judged resemblance",
  "Actual CMU measured human walking on THIS MPFB hero mesh",
  "Morphology calibration to centimeters and independent OOD holdout",
  "4K multi-shot cinematic review or production CharacterPack acceptance"],
 "production_release":"HOLD"
}
(a.out/"r014_hero_lookdev_coverage.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("R014_HERO_VISUAL_MATERIAL_GAP_AUDIT",json.dumps({
 "sex":a.sex,"skin_materials":len(body_mat),"source_mesh_count":len(meshes),
 "accessory_categories_present":{k:bool(v) for k,v in receipt["observed_named_accessories"].items()},
 "views":len(views),"status":receipt["aesthetic_status"]},sort_keys=True),flush=True)
