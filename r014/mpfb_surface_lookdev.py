"""Research-only MPFB CC0 native skin/eyes/teeth/hair lookdev candidate.
Requires official system pack digest verified by external workflow.
No genitals/whole-body anatomy/physics/video realism acceptance implied.
"""
import argparse,importlib,json,sys
from pathlib import Path
import addon_utils,bpy
from mathutils import Vector

def service(suffix,name):
    for module in list(sys.modules):
        if module.endswith(suffix):
            m=importlib.import_module(module)
            if hasattr(m,name):return getattr(m,name)
    raise RuntimeError("MPFB extension service missing "+suffix+" "+name)

p=argparse.ArgumentParser()
p.add_argument("--assets",type=Path,required=True)
p.add_argument("--output",type=Path,required=True)
p.add_argument("--receipt",type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
assert a.assets.is_dir(),"Asset directory not present"
a.output.mkdir(parents=True,exist_ok=True)
addon="bl_ext.r014lab.mpfb"
if addon not in bpy.context.preferences.addons:
    addon_utils.enable(addon,default_set=False)
assert addon in bpy.context.preferences.addons
Human=service("mpfb.services.humanservice","HumanService")
Target=service("mpfb.services.targetservice","TargetService")
Props=service("mpfb.entities.objectproperties","HumanObjectProperties")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
receipt={"status":"BLOCKED","blender":bpy.app.version_string,
         "source_license":"MPFB makehuman_system_assets_cc0, official catalog, per-asset recheck required",
         "characters":[]}
for sex,gender,x,skin,hair in (
    ("female",1.0,-.85,"young_caucasian_female","long01"),
    ("male",0.0,.85,"young_caucasian_male","short01")
):
    body=Human.create_human()
    Props.set_value("gender",gender,entity_reference=body)
    Target.reapply_macro_details(body)
    rig=Human.add_builtin_rig(body,"default")
    rig.location.x=x
    body.name="R014_"+sex+"_textured_body"
    rig.name="R014_"+sex+"_textured_rig"
    mhmat=a.assets/"skins"/skin/(skin+".mhmat")
    assert mhmat.is_file(),str(mhmat)
    Human.set_character_skin(str(mhmat),body,skin_type="ENHANCED_SSS")
    assets=[
      ("eyes","high-poly","Eyes","PROCEDURAL_EYES"),
      ("teeth","teeth_base","Teeth","MAKESKIN"),
      ("tongue","tongue01","Tongue","MAKESKIN"),
      ("eyebrows","eyebrow001","Eyebrows","MAKESKIN"),
      ("eyelashes","eyelashes01","Eyelashes","MAKESKIN"),
      ("hair",hair,"Hair","MAKESKIN"),
    ]
    added=[]
    for cat,name,asset_type,material in assets:
        path=a.assets/cat/name/(name+".mhclo")
        assert path.is_file(),str(path)
        obj=Human.add_mhclo_asset(str(path),body,asset_type=asset_type,
                                 subdiv_levels=0,material_type=material,
                                 set_up_rigging=True)
        assert obj is not None and obj.type=="MESH",("asset add failed",cat,name)
        added.append({"category":cat,"name":name,"vertices":len(obj.data.vertices)})
    bpy.context.view_layer.update()
    assert body.active_material is not None,sex+" skin material missing"
    assert len(added)==6
    receipt["characters"].append({
      "sex":sex,"body_vertices":len(body.data.vertices),
      "bones":len(rig.data.bones),"skin_material":body.active_material.name,
      "part_assets":added
    })

scene=bpy.context.scene
scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=12
scene.render.threads_mode="FIXED"
scene.render.threads=4
scene.render.resolution_x=512
scene.render.resolution_y=512
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
world=bpy.data.worlds.new("R014StudioWorld")
world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Color"].default_value=(.65,.69,.73,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.75
scene.world=world
lamp_data=bpy.data.lights.new("R014StudioKey","AREA")
lamp=bpy.data.objects.new("R014StudioKey",lamp_data)
bpy.context.collection.objects.link(lamp)
lamp.location=(1,-2,3)
lamp_data.energy=600
lamp_data.size=3
camdata=bpy.data.cameras.new("R014HeroPortrait")
cam=bpy.data.objects.new("R014HeroPortrait",camdata)
bpy.context.collection.objects.link(cam);scene.camera=cam
camdata.type="ORTHO";camdata.ortho_scale=.67

# Internal asset paths would disappear with disposable VM, so embed textures
# into native .blend before moving the artifact out of the runner.
bpy.ops.file.pack_all()
scene.render.filepath=""
blend=a.output/"R014_MPFB_CC0_surface_study.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
for sex,x in (("female",-.85),("male",.85)):
    cam.location=(x,-2.8,1.62)
    cam.rotation_euler=(Vector((x,0,1.59))-cam.location).to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=str(a.output/(sex+"_skin_eyes_hair.png"))
    bpy.ops.render.render(write_still=True)
    assert Path(scene.render.filepath).stat().st_size>10000

# Deliberately reveal complete body neutral silhouettes instead of relying on a
# face-only proof. Surface anatomy remains unqualified until a region mask review.
scene.render.resolution_x=640
scene.render.resolution_y=768
camdata.ortho_scale=3.65
for view,loc in (("fullbody_pair_front",(0,-6.1,1.43)),
                 ("fullbody_pair_back",(0,6.1,1.43))):
    cam.location=loc
    cam.rotation_euler=(Vector((0,0,1.07))-cam.location).to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=str(a.output/(view+".png"))
    bpy.ops.render.render(write_still=True)
    assert Path(scene.render.filepath).stat().st_size>10000

receipt.update({"status":"PASS_ASSET_ATTACH_AND_RENDER_UNREVIEWED",
                "native_blend":blend.name,
                "views":["female_skin_eyes_hair.png","male_skin_eyes_hair.png",
                         "fullbody_pair_front.png","fullbody_pair_back.png"],
                "asset_archive_sha256":"b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107",
                "limits":["No complete external reproductive organ meshes",
                          "Skin/hair quality and rig contact not visually accepted",
                          "No facial visemes, soft tissue dynamics or moving-body video",
                          "This lookdev scene is separate from the production body topology"]})
a.receipt.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("R014_MPFB_SURFACE",json.dumps(receipt,sort_keys=True))
