"""W2B source-custody camera and *evaluated weighted mesh* witness.

Runs only on source-original Blender scenes. Native bpy_extras projection is
provided as an independent falsifier for a separate stdlib camera implementation.
This is NOT truth about human anatomy, skin quality or contact.
"""
import argparse
import hashlib
import json
from pathlib import Path
import bpy
from bpy_extras.object_utils import world_to_camera_view

NAMES=("CobaltOriginal","MarigoldOriginal")
FRAMES=(0,12,24,36,48,60,71)


def observe(blend,video,native,out):
    blend,video,native,out=map(Path,(blend,video,native,out))
    native_data=json.loads(native.read_text())
    if native_data.get("source_rights")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC":
        raise ValueError("SOURCE_RIGHTS")
    if hashlib.sha256(blend.read_bytes()).hexdigest()!=native_data.get("blend_sha256"):
        raise ValueError("BLEND_SOURCE_SHA")
    if hashlib.sha256(video.read_bytes()).hexdigest()!=native_data.get("video_sha256"):
        raise ValueError("VIDEO_SOURCE_SHA")
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    sc=bpy.context.scene
    camera=sc.camera
    if camera is None or camera.type!="CAMERA" or camera.data.type!="ORTHO" or sc.render.resolution_percentage!=100:
        raise ValueError("CALIBRATED_ORTHO_CAMERA_REQUIRED")
    width,height=sc.render.resolution_x,sc.render.resolution_y
    if width<64 or height<64 or width>640 or height>360:
        raise ValueError("CAMERA_OUTPUT_BOUNDS")
    if sc.render.pixel_aspect_x!=1 or sc.render.pixel_aspect_y!=1:
        raise ValueError("PIXEL_ASPECT_UNSUPPORTED")
    assets={}
    for actor in NAMES:
        obj=bpy.data.objects.get(actor+"_SkinnedMesh")
        if obj is None or obj.type!="MESH" or not any(m.type=="ARMATURE" for m in obj.modifiers):
            raise ValueError("WEIGHTED_ACTOR_MESH_NOT_FOUND")
        assets[actor]=obj
    camera_matrix=[[float(camera.matrix_world[i][j]) for j in range(4)] for i in range(4)]
    witness={"schema":"scp.visualqa.w2b_scene_projection.v1",
             "rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
             "blend_sha256":native_data["blend_sha256"],
             "video_sha256":native_data["video_sha256"],
             "camera":{"projection":"ORTHOGRAPHIC","width":width,"height":height,
                       "ortho_scale":float(camera.data.ortho_scale),
                       "matrix_world":camera_matrix,
                       "pixel_aspect":[1,1]},
             "frames":[]}
    for tick in FRAMES:
        sc.frame_set(tick)
        bpy.context.view_layer.update()
        pts=[]
        for name,obj in assets.items():
            obj_eval=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            eval_mesh=obj_eval.to_mesh()
            try:
                if len(eval_mesh.vertices)!=56:
                    raise ValueError("ORIGINAL_SOURCE_WEIGHTED_VERTEX_COVERAGE")
                for idx,v in enumerate(eval_mesh.vertices):
                    xyz=obj_eval.matrix_world @ v.co
                    uv=world_to_camera_view(sc,camera,xyz)
                    pts.append({"actor":name,"vertex":idx,
                                "world_xyz":[float(x) for x in xyz],
                                "native_xy":[float(uv.x),float(uv.y)],
                                "native_depth":float(uv.z)})
            finally:
                obj_eval.to_mesh_clear()
        witness["frames"].append({"tick":tick,"mesh_points":pts})
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(witness,sort_keys=True,indent=2)+"\n")
    print("W2B_NATIVE_PROJECTION_SAMPLED",len(FRAMES),len(witness["frames"][0]["mesh_points"]))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for field in ("blend","video","native","out"):
        p.add_argument("--"+field,required=True)
    a=p.parse_args()
    observe(a.blend,a.video,a.native,a.out)
