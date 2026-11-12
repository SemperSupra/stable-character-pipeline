"""Source-native CC0 textured adult body macro variation and deformation falsifier.

Uses the independently pinned public MPFB/MAKESKIN lookdev Blender scene.
Does NOT certify photorealism, anatomical completeness or mesh-to-asset fit.
"""
import argparse
import hashlib
import importlib
import json
import math
import subprocess
import sys
from pathlib import Path

import addon_utils
import bpy
from mathutils import Vector

EXACT_PACK="b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107"
OFFICIAL_MPFB="6ff1eb358f6c1959ced77e79e6dd2406d9a71f49"
TARGET={
    "female":{"gender":0.0,"height":0.78,"weight":0.67,"muscle":0.72,"proportions":0.62},
    "male":{"gender":1.0,"height":0.30,"weight":0.83,"muscle":0.52,"proportions":0.78},
}

def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def service(suffix,name):
    for n in list(sys.modules):
        if n.endswith(suffix):
            m=importlib.import_module(n)
            if hasattr(m,name):return getattr(m,name)
    raise RuntimeError("No native pinned MPFB service "+suffix+" "+name)

def bounds(obj):
    x=[v.co for v in obj.data.vertices]
    return [round(max(float(v[i]) for v in x)-min(float(v[i]) for v in x),6) for i in range(3)]

def pts(obj):
    dg=bpy.context.evaluated_depsgraph_get()
    ev=obj.evaluated_get(dg);mesh=ev.to_mesh()
    try:return [tuple(ev.matrix_world@v.co) for v in mesh.vertices]
    finally:ev.to_mesh_clear()

def contains_parent(obj,root):
    p=obj
    while p:
        if p==root:return True
        p=p.parent
    return False

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--sex",choices=("female","male"),required=True)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--generation",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    assert Path(bpy.data.filepath).resolve()==a.source.resolve()
    a.out.mkdir(parents=True,exist_ok=True)
    gen=json.loads(a.generation.read_text())
    assert gen["asset_archive_sha256"]==EXACT_PACK
    assert gen["eye_material_mode"]=="MAKESKIN"
    assert {(c["sex"],c["source_gender_macro"]) for c in gen["characters"]}=={("female",0.0),("male",1.0)}
    assert gen["blender"]=="4.5.16 LTS"
    addon="bl_ext.r014lab.mpfb"
    if addon not in bpy.context.preferences.addons:
        addon_utils.enable(addon,default_set=False)
    assert addon in bpy.context.preferences.addons
    Props=service("mpfb.entities.objectproperties","HumanObjectProperties")
    TargetService=service("mpfb.services.targetservice","TargetService")
    body=bpy.data.objects["R014_"+a.sex+"_textured_body"]
    rig=bpy.data.objects["R014_"+a.sex+"_textured_rig"]
    other="male" if a.sex=="female" else "female"
    opposite_rig=bpy.data.objects["R014_"+other+"_textured_rig"]
    assert len(body.data.vertices)==19158 and len(rig.data.bones)==163
    assert len([m for m in body.modifiers if m.type=="ARMATURE" and m.object==rig])==1
    assert body.active_material is not None and body.active_material.use_nodes
    # Author-pinned MAKESKIN may use a custom node network rather than a
    # top-level BSDF_PRINCIPLED. Test the actual live material surface output
    # rather than requiring an irrelevant implementation detail.
    shader_nodes=list(body.active_material.node_tree.nodes)
    outputs=[n for n in shader_nodes if n.type=="OUTPUT_MATERIAL" and n.is_active_output]
    if not outputs:
        raise RuntimeError("SOURCE_MATERIAL_NO_ACTIVE_OUTPUT")
    if not any(inp.name=="Surface" and inp.is_linked for out in outputs for inp in out.inputs):
        raise RuntimeError("SOURCE_MATERIAL_OUTPUT_SURFACE_NOT_CONNECTED")
    shader_contract={"active_output_count":len(outputs),
                     "node_types":sorted({n.type for n in shader_nodes}),
                     "surface_linked":True}
    packed=[img for img in bpy.data.images if img.source=="FILE" and img.packed_file is not None]
    assert len(packed)>=1,"No packed CC0 source textures"
    source_bounds=bounds(body)
    source_pts=pts(body)
    for k,v in TARGET[a.sex].items():
        assert 0.0<=v<=1.0
        Props.set_value(k,v,entity_reference=body)
    Props.set_value("age",0.65,entity_reference=body)
    TargetService.reapply_macro_details(body)
    bpy.context.view_layer.update()
    changed_pts=pts(body)
    assert len(changed_pts)==len(source_pts)
    diff=max(math.dist(a,b) for a,b in zip(source_pts,changed_pts))
    assert diff>1e-4,("macro had no real vertex response",diff)
    after_bounds=bounds(body)
    report={
        "schema":"r014.cc0.textured_body_morph_integrity.v1",
        "status":"STRUCTURAL_INCOMPLETE",
        "source_github_actions_run":43207664661,
        "source_github_actions_artifact":"r014-mpfb-eye-MAKESKIN-lookdev",
        "source_mpbf":OFFICIAL_MPFB,
        "source_official_pack_sha256":EXACT_PACK,
        "source_blend_sha256":sha(a.source),
        "sex_macro_label":a.sex,
        "gender_macro_value":TARGET[a.sex]["gender"],
        "adult_design_only":True,
        "age_macro":0.65,
        "age_macro_not_chronological_age":True,
        "source_macros":TARGET[a.sex],
        "source_body_bounds_xyz_blender_units":source_bounds,
        "after_body_bounds_xyz_blender_units":after_bounds,
        "real_body_vertices":len(body.data.vertices),
        "rig_bones":len(rig.data.bones),
        "real_morph_max_vertex_delta_blender_units":round(diff,6),
        "packed_source_texture_count":len(packed),
        "original_material":body.active_material.name,
        "original_material_shader_contract":shader_contract,
        "same_lod_rig":"native rig retained after applying source macro",
        "photoreal_quality":"HOLD_VISUAL_AND_ANATOMICAL_REVIEW",
        "soft_tissue_physics":"NOT_RUN",
        "external_reproductive_anatomy":"NOT_QUALIFIED",
        "full_accessory_fit":"NOT_QUALIFIED",
        "merge_release":"HOLD",
        "limitations":["CC0 texture/hair assets inherited; not new 3D texture synthesis",
                       "Does not determine actual identity or chronological age",
                       "Missing actual garment/hair fit oracle, collision, anatomical surface closeness",
                       "Not motion retargeting, realistic gait or cinematic appearance qualification"]
    }
    # The original source includes two actors. Show only this actor and its
    # MPFB accessory meshes (hair, brows, lashes, eyes, teeth, tongue).
    for obj in bpy.data.objects:
        if contains_parent(obj,opposite_rig) or (obj.type=="MESH" and obj.name.startswith("R014_"+other)):
            obj.hide_render=True
            obj.hide_set(True)
    assert not body.hide_render
    for n in ("upperarm01.L","upperleg01.L"):
        assert n in rig.pose.bones
        pose=rig.pose.bones[n]
        pose.rotation_mode="XYZ"
        for frame,angle in ((1,0),(8,0.32 if n.startswith("upperarm") else -0.22),(16,0)):
            pose.rotation_euler=(0,angle,0)
            pose.keyframe_insert(data_path="rotation_euler",frame=frame)
    scene=bpy.context.scene
    scene.frame_start=1;scene.frame_end=16;scene.render.fps=12
    scene.frame_set(1);bpy.context.view_layer.update()
    rest=pts(body)
    scene.frame_set(8);bpy.context.view_layer.update()
    motion=pts(body)
    motiondiff=max(math.dist(a,b) for a,b in zip(rest,motion))
    assert motiondiff>1e-4,"lost rigged skin motion"
    scene.frame_set(16);bpy.context.view_layer.update()
    restored=pts(body)
    motionres=max(math.dist(a,b) for a,b in zip(rest,restored))
    assert motionres<1e-4,"failed restorative pose"
    report["actual_rig_pose_max_deformation_blender_units"]=round(motiondiff,6)
    report["actual_rig_pose_return_error_blender_units"]=round(motionres,9)
    scene.frame_set(1)
    camdata=bpy.data.cameras.new("R014_CC0_Morph_Camera_"+a.sex)
    cam=bpy.data.objects.new(camdata.name,camdata);bpy.context.collection.objects.link(cam)
    camdata.type="ORTHO";camdata.ortho_scale=3.0;scene.camera=cam
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU";scene.cycles.samples=9
    scene.render.threads_mode="FIXED";scene.render.threads=4
    scene.render.resolution_x=420;scene.render.resolution_y=530
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.film_transparent=False
    x=float(rig.location.x)
    for view,pose in (("front",1),("back",1),("posed",8)):
        scene.frame_set(pose)
        if view=="front":cam.location=(x,-5.2,1.65)
        elif view=="back":cam.location=(x,5.2,1.65)
        else:cam.location=(x+1.3,-5.2,1.65)
        cam.rotation_euler=(Vector((x,0,1.02))-cam.location).to_track_quat("-Z","Y").to_euler()
        image=a.out/(a.sex+"_cc0_morph_"+view+".png")
        scene.render.filepath=str(image)
        bpy.ops.render.render(write_still=True)
        assert image.is_file() and image.stat().st_size>3000
        report.setdefault("rendered_stills",[]).append({"name":image.name,"sha256":sha(image)})
    # Native scene with all reusable assets/rig/animation and packed textures.
    scene.frame_set(1)
    scene.render.filepath=""
    bpy.ops.file.pack_all()
    native=a.out/("R014_"+a.sex+"_CC0_morph_editable_motion.blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(native))
    assert native.stat().st_size>5_000_000
    report["editable_blend"]={"name":native.name,"bytes":native.stat().st_size,"sha256":sha(native)}
    cam.location=(x+0.5,-5.2,1.65)
    cam.rotation_euler=(Vector((x,0,1.02))-cam.location).to_track_quat("-Z","Y").to_euler()
    scene.render.resolution_x=288;scene.render.resolution_y=380
    scene.render.image_settings.file_format="FFMPEG"
    scene.render.ffmpeg.format="MPEG4"
    scene.render.ffmpeg.codec="H264"
    scene.render.ffmpeg.constant_rate_factor="HIGH"
    scene.render.ffmpeg.ffmpeg_preset="GOOD"
    prefix="R014_"+a.sex+"_CC0_morph_actual_skin_motion"
    scene.render.filepath=str(a.out/(prefix+".mp4"))
    bpy.ops.render.render(animation=True)
    movies=sorted(a.out.glob(prefix+"*.mp4"))
    assert len(movies)==1 and movies[0].stat().st_size>512
    movie=movies[0]
    out=subprocess.run(["ffprobe","-v","error","-select_streams","v:0",
       "-show_entries","stream=codec_name,width,height,nb_frames",
       "-show_entries","format=duration","-of","json",str(movie)],
       check=True,capture_output=True,text=True,timeout=25)
    meta=json.loads(out.stdout)
    v=meta["streams"][0]
    assert v["codec_name"]=="h264"
    assert (int(v["width"]),int(v["height"]))==(288,380)
    assert int(v["nb_frames"])==16
    assert 1.0<float(meta["format"]["duration"])<1.6
    report["real_motion_video"]={"name":movie.name,"bytes":movie.stat().st_size,
                                 "sha256":sha(movie),"probe":meta,
                                 "motion":"actuated real body/rig; not validated gait"}
    report["status"]="PASS_SOURCE_NATIVE_CC0_MORPH_MOTION_RENDER_STRUCTURAL_ONLY"
    (a.out/"morph_receipt.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("R014_CC0_MORPH",json.dumps(report,sort_keys=True))

if __name__=="__main__":main()
