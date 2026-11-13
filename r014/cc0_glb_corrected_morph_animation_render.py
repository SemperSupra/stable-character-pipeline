"""R014 actual corrected full adult source GLB: native morphology + motion readiness.

Runs ONLY on independently imported glTF in a clean Blender process.
Preserves editable .blend, 2 technical Cycles PNGs, 16-frame true H.264,
and fails closed unless both a live native body shape key and skin animation
actually deform and restore measured evaluated 3D vertices.
Cinematic photorealism, complete anatomy and contact quality remain HOLD.
"""
import argparse
from hashlib import sha256
import json
import math
import subprocess
import sys
from pathlib import Path
import bpy
from mathutils import Vector

def digest(path):
    h=sha256()
    with Path(path).open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):h.update(c)
    return h.hexdigest()

def sample_points(obj):
    dep=bpy.context.evaluated_depsgraph_get()
    evaluated=obj.evaluated_get(dep)
    m=evaluated.to_mesh()
    try:
        indices=sorted({int(i*(len(m.vertices)-1)/1023) for i in range(1024)})
        return [evaluated.matrix_world@m.vertices[i].co for i in indices]
    finally:evaluated.to_mesh_clear()

def delta(a,b):
    assert len(a)==len(b)
    return max((p-q).length for p,q in zip(a,b))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--glb",type=Path,required=True)
    p.add_argument("--export-receipt",type=Path,required=True)
    p.add_argument("--sex",choices=("female","male"),required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    assert Path(bpy.data.filepath).resolve()==a.source.resolve()
    a.out.mkdir(parents=True,exist_ok=True)
    original=json.loads(a.export_receipt.read_text())
    assert original["sex"]==a.sex
    assert original["strategy"]=="mpfb_mask_bake"
    assert original["status"]=="PASS_EXPERIMENTAL_GLTF_EXPORT_ONLY_NEEDS_INDEPENDENT_GEOMETRY_PARITY"
    assert original["generated_portable_glb"]["sha256"]==digest(a.glb)
    assert original["generated_portable_glb"]["morph_target_meshes"]>=1
    body=bpy.data.objects["R014_"+a.sex+"_textured_body"]
    rig=bpy.data.objects["R014_"+a.sex+"_textured_rig"]
    assert body.type=="MESH" and rig.type=="ARMATURE"
    assert len(rig.data.bones)==163
    assert len(body.data.vertices)>=13000
    skinned=[m for m in body.modifiers if m.type=="ARMATURE" and m.object==rig]
    assert len(skinned)>=1
    actors=[o for o in bpy.data.objects if o.type=="MESH" and o.name.startswith("R014_"+a.sex+"_textured_body")]
    assert len(actors)>=7,"COLD_IMPORT_MISSING_ACCESSORIES"
    keys=body.data.shape_keys.key_blocks if body.data.shape_keys else []
    expected=30 if a.sex=="female" else 20
    assert len(keys)==expected,("MORPH_TARGETS_DROPPED",a.sex,len(keys),expected)
    source_nonzero=[k for k in keys if k.name.lower()!="basis" and abs(float(k.value))>1e-5]
    assert source_nonzero,"NO_ACTIVE_MPFB_SHAPE_CONTROLS"
    scene=bpy.context.scene
    actions=[(act.name,float(act.frame_range[0]),float(act.frame_range[1])) for act in bpy.data.actions]
    assert actions
    start=math.floor(min(v[1] for v in actions));end=math.ceil(max(v[2] for v in actions))
    middle=round((start+end)/2)
    assert end-start>=10
    scene.frame_set(start);bpy.context.view_layer.update()
    original_points=sample_points(body)
    scene.frame_set(middle);bpy.context.view_layer.update()
    mid_points=sample_points(body)
    movement=delta(original_points,mid_points)
    assert movement>0.001,("ACTUAL_GLTF_SKIN_MOTION_MISSING",movement)
    scene.frame_set(end);bpy.context.view_layer.update()
    final_points=sample_points(body)
    repeat=delta(original_points,final_points)
    assert repeat<0.0005,("ACTUAL_GLTF_SKIN_RETURN_FAILED",repeat)
    scene.frame_set(start);bpy.context.view_layer.update()
    key=source_nonzero[0]
    initial=float(key.value)
    target=initial+0.025 if initial<=0.95 else initial-0.025
    key.value=target
    bpy.context.view_layer.update()
    actuated=sample_points(body)
    morph_delta=delta(original_points,actuated)
    key.value=initial
    bpy.context.view_layer.update()
    round_trip=delta(original_points,sample_points(body))
    assert morph_delta>1e-5,("ACTUAL_GLTF_BODY_SHAPE_MORPH_MISSING",key.name,morph_delta)
    assert round_trip<1e-5,("SHAPE_MORPH_NONREVERSIBLE",round_trip)
    report={
      "schema":"r014.cc0.cold_glb_real_morph_and_animated_skin.v1",
      "status":"PASS_ACTUAL_NATIVE_MASK_BAKED_GLTF_MORPH_AND_MOTION_STRUCTURAL_ONLY",
      "sex_macro":a.sex,
      "model_source_mpbf":"6ff1eb358f6c1959ced77e79e6dd2406d9a71f49",
      "source_original_gltf_problem":"MASK_MODIFIER_EXPORT_UNBAKED_HELPERS_PREVIOUSLY_FAILED",
      "selected_solution":"official native MPFB ExportService.bake_modifiers_remove_helpers",
      "corrected_source_glb_sha256":digest(a.glb),
      "cold_source_blend":a.source.name,"cold_source_blend_sha256":digest(a.source),
      "rig_bones":len(rig.data.bones),"actual_morph_targets":len(keys),
      "actual_rendered_meshes":len(actors),
      "glb_actual_source_active_key_tested":key.name,
      "source_key_value":initial,"test_changed_value":target,
      "actual_key_deformation_max_blender_native":round(morph_delta,9),
      "source_shape_restoration_error_blender_native":round(round_trip,10),
      "skin_action_frames":[start,middle,end],
      "actual_skin_max_motion_blender_native":round(movement,9),
      "source_skin_return_error_blender_native":round(repeat,10),
      "source_reimport_mesh_world_area_fidelity":"INDEPENDENT_SOURCE_PARITY_AUDIT_REQUIRED",
      "sex_morph_macro_is_not_gender_identity":True,
      "source_young_old_morph_keys_are_not_age_evidence":True,
      "anatomical_and_organ_completeness":"HOLD",
      "real_foot_ground_gait":"HOLD",
      "source_PBR_skin_eyes_hair":"TECHNICAL_NOT_CINEMATIC",
      "collision_and_tissue_physics":"HOLD",
      "CPE_semantics_or_generation_eligibility":"SEPARATE_PIPELINE",
      "merge_release":"HOLD"
    }
    # Render newly imported, not the author source.
    scene.frame_set(start)
    points=sample_points(body)
    low=[min(float(v[j]) for v in points) for j in range(3)]
    high=[max(float(v[j]) for v in points) for j in range(3)]
    center=Vector(tuple((a+b)/2 for a,b in zip(low,high)))
    camera_data=bpy.data.cameras.new("R014_CorrectedGLB_ReviewCamera")
    camera=bpy.data.objects.new("R014_CorrectedGLB_ReviewCamera",camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera=camera
    camera_data.type="ORTHO";camera_data.ortho_scale=max(2.5,(high[2]-low[2])*1.35)
    camera.location=(center.x,center.y-5.8,center.z)
    camera.rotation_euler=(center-camera.location).to_track_quat("-Z","Y").to_euler()
    light_data=bpy.data.lights.new("R014_GLBFix_Area","AREA")
    light=bpy.data.objects.new("R014_GLBFix_Area",light_data)
    bpy.context.collection.objects.link(light)
    light.location=(center.x+2.,center.y-3.,center.z+2.)
    light_data.energy=550;light_data.size=5
    scene.render.engine="CYCLES";scene.cycles.device="CPU";scene.cycles.samples=12
    scene.render.threads_mode="FIXED";scene.render.threads=4
    scene.render.resolution_x=576;scene.render.resolution_y=760
    scene.render.resolution_percentage=100
    scene.render.film_transparent=False
    scene.render.image_settings.file_format="PNG"
    for label,frame in (("front",start),("posed",middle)):
        scene.frame_set(frame)
        image=a.out/(a.sex+"_corrected_maskbake_GLTF_"+label+".png")
        scene.render.filepath=str(image)
        bpy.ops.render.render(write_still=True)
        assert image.stat().st_size>5000
        report.setdefault("imported_real_Cycles_stills",[]).append({"name":image.name,"sha256":digest(image)})
    scene.frame_set(start)
    scene.render.filepath=""
    bpy.ops.file.pack_all()
    native=a.out/("R014_"+a.sex+"_corrected_maskbake_GLTF_editable.blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(native))
    report["imported_editable_native"]={"name":native.name,"bytes":native.stat().st_size,"sha256":digest(native)}
    scene.render.resolution_x=320;scene.render.resolution_y=420
    scene.render.image_settings.file_format="FFMPEG"
    scene.render.ffmpeg.format="MPEG4";scene.render.ffmpeg.codec="H264"
    scene.render.ffmpeg.ffmpeg_preset="GOOD"
    scene.frame_start=start;scene.frame_end=end;scene.frame_step=2;scene.render.fps=12
    prefix="R014_"+a.sex+"_corrected_maskbake_GLTF_actual_motion"
    scene.render.filepath=str(a.out/(prefix+".mp4"))
    bpy.ops.render.render(animation=True)
    movies=list(a.out.glob(prefix+"*.mp4"))
    assert len(movies)==1 and movies[0].stat().st_size>512
    result=subprocess.run(["ffprobe","-v","error","-select_streams","v:0",
       "-show_entries","stream=codec_name,width,height,nb_frames",
       "-show_entries","format=duration","-of","json",str(movies[0])],
       capture_output=True,text=True,check=True,timeout=25)
    meta=json.loads(result.stdout)
    stream=meta["streams"][0]
    assert stream["codec_name"]=="h264"
    assert (int(stream["width"]),int(stream["height"]))==(320,420)
    assert int(stream["nb_frames"])>=14
    report["corrected_imported_animated_H264"]={
       "name":movies[0].name,"sha256":digest(movies[0]),"bytes":movies[0].stat().st_size,
       "metadata":meta}
    (a.out/"corrected_morph_motion_receipt.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("R014_CORRECTED_FULL_HUMAN_GLTF",json.dumps({
        "sex":a.sex,"status":report["status"],"morph_keys":len(keys),
        "actual_delta":report["actual_key_deformation_max_blender_native"],
        "morph_rest_error":report["source_shape_restoration_error_blender_native"],
        "motion":report["actual_skin_max_motion_blender_native"],
        "motion_rest_error":report["source_skin_return_error_blender_native"],
        "video_frames":stream["nb_frames"],
        "glb":report["corrected_source_glb_sha256"]
    },sort_keys=True))
if __name__=="__main__":main()
