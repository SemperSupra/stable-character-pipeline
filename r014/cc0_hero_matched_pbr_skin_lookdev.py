"""Controlled source-native CC0 adult hero skin look-development bakeoff.

Genuine Blender full-body rig/materials/textures from independently reimported
CC0 MPFB source. Renders unchanged BASELINE and conservative PBR experimental
skin using identical Blender camera, light and scene, metrics in JSON. Only
technical lookdev; photoreal acceptance requires independent human reviewer.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

ap=argparse.ArgumentParser()
ap.add_argument("--sex",choices=("female","male"),required=True)
ap.add_argument("--mode",choices=("baseline","skin-sss-microbump"),required=True)
ap.add_argument("--source",type=Path,required=True)
ap.add_argument("--source-receipt",type=Path,required=True)
ap.add_argument("--out",type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
assert Path(bpy.data.filepath).resolve()==a.source.resolve()
a.out.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
 return h.hexdigest()
r=json.loads(a.source_receipt.read_text())
assert r["status"]=="PASS_ACTUAL_NATIVE_MASK_BAKED_GLTF_MORPH_AND_MOTION_STRUCTURAL_ONLY"
assert r["sex_macro"]==a.sex
assert r["imported_editable_native"]["sha256"]==sha(a.source)
assert r["merge_release"]=="HOLD"
body=bpy.data.objects["R014_"+a.sex+"_textured_body"]
rig=bpy.data.objects["R014_"+a.sex+"_textured_rig"]
assert body.type=="MESH" and rig.type=="ARMATURE"
assert body.parent is rig
assert len(rig.data.bones)==163 and len(body.data.vertices)==14926
assert len(body.data.shape_keys.key_blocks)==(30 if a.sex=="female" else 20)
assert len(body.data.uv_layers)>0
assert len(body.data.materials)==6
scene=bpy.context.scene
scene.frame_set(2)
bpy.context.view_layer.update()
mats={mat.name:mat for mat in body.data.materials if mat}
assert len(mats)==6
for name,mat in mats.items():
 assert mat.use_nodes
 bs=[n for n in mat.node_tree.nodes if n.type=="BSDF_PRINCIPLED"]
 assert len(bs)==1 and "Subsurface Weight" in bs[0].inputs
 assert "Roughness" in bs[0].inputs
# Original baseline surface has zero SSS; the experiment does not claim
# physically measured skin thickness or photographic scan/material quality.
before={k:{"roughness":float(next(n for n in m.node_tree.nodes if n.type=="BSDF_PRINCIPLED").inputs["Roughness"].default_value),
           "subsurface":float(next(n for n in m.node_tree.nodes if n.type=="BSDF_PRINCIPLED").inputs["Subsurface Weight"].default_value),
           "image_nodes":sum(n.type=="TEX_IMAGE" for n in m.node_tree.nodes),
           "bump_nodes":sum(n.type=="BUMP" for n in m.node_tree.nodes)} for k,m in mats.items()}
assert all(v["subsurface"]==0 for v in before.values())
change=[]
if a.mode=="skin-sss-microbump":
 for name,mat in mats.items():
  bsdf=next(n for n in mat.node_tree.nodes if n.type=="BSDF_PRINCIPLED")
  if name.endswith(".body"):
   bsdf.inputs["Subsurface Weight"].default_value=.13
   bsdf.inputs["Roughness"].default_value=.44
   if bsdf.inputs.get("Subsurface Scale"):
    bsdf.inputs["Subsurface Scale"].default_value=.004
   node_tex=mat.node_tree.nodes.new("ShaderNodeTexNoise")
   node_tex.name="R014_ExperimentalSkinMicronoise"
   node_tex.inputs["Scale"].default_value=165.
   node_tex.inputs["Detail"].default_value=3.
   node_tex.inputs["Roughness"].default_value=.7
   node_bump=mat.node_tree.nodes.new("ShaderNodeBump")
   node_bump.name="R014_ExperimentalSkinMicrobump"
   node_bump.inputs["Strength"].default_value=.18
   node_bump.inputs["Distance"].default_value=.00012
   existing=bsdf.inputs["Normal"].links
   if existing:
    link=existing[0]
    original_from=link.from_socket
    mat.node_tree.links.remove(link)
    mat.node_tree.links.new(original_from,node_bump.inputs["Normal"])
   mat.node_tree.links.new(node_tex.outputs["Fac"],node_bump.inputs["Height"])
   mat.node_tree.links.new(node_bump.outputs["Normal"],bsdf.inputs["Normal"])
   change.append({"material":name,"sss":.13,"roughness":.44,
      "noise_scale":165.,"bump_strength":.18,"bump_distance_Blender_units":.00012,
      "source_physical_calibration":"NONE"})
  elif name.endswith((".lips",".ears")):
   bsdf.inputs["Subsurface Weight"].default_value=.055
   change.append({"material":name,"sss":.055})
assert (len(change)>=3) if a.mode=="skin-sss-microbump" else (len(change)==0)

# Original glTF reimport contains unrelated default Blender primitives;
# only remove them from visual staging, source assets remain untouched.
unrelated=[]
for obj in bpy.data.objects:
 if obj.type=="MESH" and obj.name in ("Cube","Icosphere"):
  obj.hide_render=True
  unrelated.append(obj.name)
assert sorted(unrelated)==["Cube","Icosphere"],"unexpected fixture mesh set"
# source original full body bounds in world, not an arbitrary camera framing.
def surface_bounds():
 deps=bpy.context.evaluated_depsgraph_get()
 obj=body.evaluated_get(deps);mesh=obj.to_mesh()
 try:
  p=np.asarray([list(obj.matrix_world@v.co) for v in mesh.vertices],float)
 finally:obj.to_mesh_clear()
 assert p.shape==(14926,3) and np.isfinite(p).all()
 return p.min(axis=0),p.max(axis=0)
lo,hi=surface_bounds()
ext=hi-lo;mid=(lo+hi)*.5
scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=20
scene.render.threads_mode="FIXED"
scene.render.threads=4
scene.render.resolution_x=720
scene.render.resolution_y=900
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
world=bpy.data.worlds.new("R014_MatchedSkinLookdevWorld")
world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.62
scene.world=world
ld=bpy.data.lights.new("R014_MatchedSkinLookdevArea","AREA")
light=bpy.data.objects.new("R014_MatchedSkinLookdevArea",ld)
bpy.context.collection.objects.link(light)
ld.energy=540;ld.size=3.5
cd=bpy.data.cameras.new("R014_MatchedSkinLookdevCamera")
cam=bpy.data.objects.new("R014_MatchedSkinLookdevCamera",cd)
bpy.context.collection.objects.link(cam)
scene.camera=cam;cd.type="ORTHO"
def render(label,focus,offset,scale):
 f=Vector(tuple(float(x) for x in focus))
 d=Vector(tuple(float(x) for x in offset))
 cam.location=f+d
 cam.rotation_euler=(f-cam.location).to_track_quat("-Z","Y").to_euler()
 cd.ortho_scale=float(scale)
 light.location=f+Vector((1.,-1.8,2.))
 scene.render.filepath=str(a.out/(a.sex+"_"+a.mode+"_"+label+".png"))
 bpy.ops.render.render(write_still=True)
 p=Path(scene.render.filepath);assert p.stat().st_size>5000
 return {"name":p.name,"sha256":sha(p),"view":label,
         "pixels":[720,900],"source_renderer":"Cycles CPU 20 samples matched lighting"}
images=[
 render("face", (mid[0],mid[1],hi[2]-.19*ext[2]),
        (0,-max(1.2,float(ext[2]*1.0)),.17),max(.6,float(ext[2])*.53)),
 render("hand", (mid[0]+.38*ext[0],mid[1],lo[2]+.54*ext[2]),
        (.25,-max(1.2,float(ext[2])),.1),max(.62,float(ext[2])*.45)),
]
after={k:{"subsurface":float(next(n for n in m.node_tree.nodes if n.type=="BSDF_PRINCIPLED").inputs["Subsurface Weight"].default_value),
          "roughness":float(next(n for n in m.node_tree.nodes if n.type=="BSDF_PRINCIPLED").inputs["Roughness"].default_value),
          "bump_nodes":sum(n.type=="BUMP" for n in m.node_tree.nodes)} for k,m in mats.items()}
if a.mode=="baseline":
 assert all(abs(after[k]["subsurface"]-before[k]["subsurface"])<1e-10 for k in mats)
else:
 assert sum(v["subsurface"]>0 for v in after.values())>=3
 assert sum(v["bump_nodes"]>0 for v in after.values())>=1
record={
 "schema":"r014.cc0.hero_skin_matched_pbr_lookdev.v1",
 "status":"PASS_MATCHED_CYCLES_RESEARCH_RENDER_ONLY",
 "aesthetic_release":"HOLD_HUMAN_PHOTOREAL_CINEMATIC_AND_ANATOMY_REVIEW",
 "subject":a.sex,"mode":a.mode,
 "source_native_editable_blend_sha256":sha(a.source),
 "source_original_GHA":43395948140,
 "source_experiment":"actual original CC0 MakeHuman full adult synthetic, no likeness",
 "skin_source_geometry_vertices":len(body.data.vertices),
 "rig_bones":len(rig.data.bones),
 "original_morph_target_count":len(body.data.shape_keys.key_blocks),
 "original_noncharacter_default_primitives_hidden":unrelated,
 "source_body_material_before":before,
 "source_body_material_after":after,
 "experimental_changes":change,
 "render_images":images,
 "original_textures_preserved":True,
 "physical_skin_thickness_and_bump_calibration":"UNKNOWN_BLENDER_NATIVE_UNITS",
 "external_anatomy_and_organ_completeness":"HOLD_NOT_VERIFIED",
 "skin_hair_eye_4K_cinematic_acceptance":"HOLD_NOT_INDEPENDENTLY_REVIEWED",
 "limits":["No matched photographic material reference, device color calibration or source optical ground truth",
   "No physically calibrated subsurface thickness, pore size, roughness distribution or hair fiber simulation",
   "No face FACS/viseme, grasp, body soft tissue, ground contact or original human gait",
   "No normative morphology/body-type/age/sex interpretation from source labels",
   "No canonical pack, protected person source or release rights from this run"],
}
(a.out/"r014_skin_lookdev_matched_receipt.json").write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
print("R014_HERO_PBR_LOOKDEV_EVIDENCE",json.dumps({
 "subject":a.sex,"mode":a.mode,"images":len(images),"changed_materials":len(change),
 "body_sss":after[next(k for k in mats if k.endswith(".body"))]["subsurface"],
 "status":record["aesthetic_release"]},sort_keys=True),flush=True)
