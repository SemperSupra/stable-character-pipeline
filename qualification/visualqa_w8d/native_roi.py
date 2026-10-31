"""W8-D optional low-resolution real native Blender QA-only AOV scope/cost probe."""
import argparse,hashlib,json,os,time
from pathlib import Path
import bpy
from mathutils import Vector
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(folder,out):
 folder=Path(folder);out=Path(out);out.mkdir(parents=True,exist_ok=True)
 receipt=json.loads((folder/"source_motion_receipt.json").read_text())
 blend=folder/"original_source_grounded_24frame_native.blend"
 if receipt.get("rights")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC" or receipt.get("blend_sha256")!=sha(blend):
  raise ValueError("W8D_BLENDER_ORIGINAL_SOURCE_SHA")
 before=sha(blend)
 bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
 scene=bpy.context.scene;scene.frame_set(0)
 eye=Vector((0.,-8.5,2.8));target=Vector((0.,0.,1.15))
 camdata=bpy.data.cameras.new("QAOnlyCameraData")
 cam=bpy.data.objects.new("QAOnlyCamera",camdata)
 scene.collection.objects.link(cam)
 cam.location=eye;cam.rotation_euler=(target-eye).to_track_quat("-Z","Y").to_euler()
 camdata.type="ORTHO";camdata.ortho_scale=5.75
 scene.camera=cam
 # QA-only fiducials, original .blend is NEVER saved or modified on disk.
 for i,x in enumerate((-1.,0.,1.)):
  bpy.ops.mesh.primitive_cube_add(size=0.07, location=(x,0.,.07))
  fid=bpy.context.object;fid.name=f"QAOnlyWorldX_{i}"
  fid["source_classification"]="QA_ONLY_NOT_BEAUTY"
  fid.color=((1.,.1,.1,1.) if x<0 else (.1,1.,.1,1.))
 scene.render.resolution_x=160;scene.render.resolution_y=90;scene.render.resolution_percentage=100
 scene.render.image_settings.color_mode="RGBA"
 scene.render.film_transparent=False
 measurements=[]
 scene.render.engine="BLENDER_WORKBENCH"
 scene.display.shading.color_type="OBJECT"
 scene.render.image_settings.file_format="PNG"
 png=out/"workbench_QA_fiducial_frame0.png";scene.render.filepath=str(png.resolve())
 t=time.monotonic();bpy.ops.render.render(write_still=True)
 measurements.append({"renderer":"BLENDER_WORKBENCH","product":"QA_ONLY_FLAT_COLOR_PNG",
  "status":"EXECUTED_IMAGE","seconds":time.monotonic()-t,
  "size":png.stat().st_size,"sha256":sha(png),
  "cycles_cryptomatte":"NOT_AVAILABLE_IN_WORKBENCH"})
 cycle={"renderer":"CYCLES","product":"QA_ONLY_MULTILAYER_EXR_160x90_FRAME0",
        "status":"NOT_RUN","aov_content_verified":"NOT_RUN"}
 if hasattr(scene,"cycles"):
  scene.render.engine="CYCLES"
  scene.cycles.device="CPU";scene.cycles.samples=2
  layer=scene.view_layers[0]
  layer.use_pass_z=True;layer.use_pass_normal=True
  cryptomatte_requested=hasattr(layer,"use_pass_cryptomatte_object")
  if cryptomatte_requested:layer.use_pass_cryptomatte_object=True
  exr=out/"cycles_QA_AOV_frame0.exr";scene.render.image_settings.file_format="OPEN_EXR_MULTILAYER"
  scene.render.filepath=str(exr.resolve())
  t=time.monotonic();bpy.ops.render.render(write_still=True)
  cycle.update({"status":"EXECUTED_FILE_ONLY","seconds":time.monotonic()-t,
    "size":exr.stat().st_size,"sha256":sha(exr),
    "cryptomatte_requested":cryptomatte_requested,
    "aov_content_verified":"UNKNOWN_NO_INDEPENDENT_EXR_CHANNEL_DECODER"})
 measurements.append(cycle)
 if sha(blend)!=before:raise ValueError("W8D_ORIGINAL_BLEND_CHANGED")
 report={"schema":"scp.visualqa_w8d.renderer_roi.v1","original_blend_sha256":before,
  "frame":0,"resolution":[160,90],"qa_only_fiducials":3,"saved_source_blend":False,
  "engine_cases":measurements,"eevee":"NOT_RUN_NO_ADMITTED_SOFTWARE_GPU_RENDERER",
  "full_frame_AOV_all_ticks":"NOT_RUN_COST_GATE","render_fidelity":"UNKNOWN_DIAGNOSTIC_PASS_ONLY",
  "human_behavior":"NOT_EVALUATED"}
 (out/"roi_manifest.json").write_text(json.dumps(report,sort_keys=True,indent=2)+chr(10))
 print("W8D_QA_ONLY_ROI_EXECUTED_NOT_HUMAN_ACCEPTANCE",report["engine_cases"])
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--artifact",required=True);p.add_argument("--out",required=True)
 a=p.parse_args();run(a.artifact,a.out)
