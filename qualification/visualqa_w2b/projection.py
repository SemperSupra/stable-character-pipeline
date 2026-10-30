"""W2B independent stdlib orthographic camera witness + actual decoded image probe.

Do not treat matching screen bbox as proof of real skin/anatomy. This is a
specific source-original Blender Workbench orthographic camera contract.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

MAX_BYTES=100_000_000


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(65536),b""):
            h.update(chunk)
    return h.hexdigest()


def project(xyz,camera):
    m=camera["matrix_world"]
    w,h=camera["width"],camera["height"]
    scale=camera["ortho_scale"]
    if (not isinstance(w,int) or not isinstance(h,int) or
        not 32<=w<=640 or not 32<=h<=360 or
        not math.isfinite(scale) or not 0<scale<100 or
        len(m)!=4 or any(len(row)!=4 for row in m) or
        any(not math.isfinite(v) for row in m for v in row) or
        len(xyz)!=3 or any(not math.isfinite(v) for v in xyz)):
        raise ValueError("CAMERA_OR_POINT_NOT_ADMITTED")
    origin=[m[i][3] for i in range(3)]
    vector=[xyz[i]-origin[i] for i in range(3)]
    right=sum(vector[i]*m[i][0] for i in range(3))
    up=sum(vector[i]*m[i][1] for i in range(3))
    back=sum(vector[i]*m[i][2] for i in range(3))
    # Ortho camera: width equals ortho_scale for landscape formats,
    # with height derived by pixel aspect. Native bpy_extras acts as oracle.
    nx=.5+right/scale
    ny=.5+up*(w/h)/scale
    return nx,ny,-back


def frame_gray(video,w,h,count):
    if w*h*count>96_000_000 or count>180:
        raise ValueError("BOUNDED_ACTUAL_IMAGE_READ")
    proc=subprocess.run(["ffmpeg","-nostdin","-v","error","-i",str(video),
                         "-map","0:v:0","-an","-f","rawvideo","-pix_fmt","gray","-"],
                        capture_output=True,check=True,timeout=90)
    if len(proc.stdout)!=w*h*count:
        raise ValueError("DECODED_FRAME_COUNT_MISMATCH")
    return [memoryview(proc.stdout)[i*w*h:(i+1)*w*h] for i in range(count)]


def bbox(points):
    if not points:
        return None
    return [min(x for x,y in points),min(y for x,y in points),
            max(x for x,y in points),max(y for x,y in points)]


def verify(manifest,video,native,out):
    p=Path(manifest)
    if p.stat().st_size>4_000_000:
        raise ValueError("MANIFEST_BOUNDED_SIZE")
    scene=json.loads(p.read_text())
    original=json.loads(Path(native).read_text())
    if (scene.get("schema")!="scp.visualqa.w2b_scene_projection.v1" or
        scene.get("rights")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC" or
        scene.get("blend_sha256")!=original.get("blend_sha256") or
        scene.get("video_sha256")!=original.get("video_sha256") or
        scene.get("video_sha256")!=sha(video) or
        original.get("source_rights")!=scene["rights"]):
        raise ValueError("SCENE_VIDEO_SOURCE_CUSTODY")
    cam=scene["camera"]
    if cam["projection"]!="ORTHOGRAPHIC" or cam["pixel_aspect"]!=[1,1]:
        raise ValueError("UNADMITTED_CAMERA_MODEL")
    w,h=cam["width"],cam["height"]
    probe=subprocess.run(["ffprobe","-v","error","-count_frames","-select_streams","v:0",
                          "-show_entries","stream=codec_name,width,height,nb_read_frames",
                          "-of","json",str(video)],capture_output=True,check=True,text=True,timeout=30)
    streams=json.loads(probe.stdout).get("streams",[])
    if len(streams)!=1 or streams[0].get("codec_name")!="h264" or        (int(streams[0]["width"]),int(streams[0]["height"]))!=(w,h):
        raise ValueError("VIDEO_CAMERA_DIMENSIONS_MISMATCH")
    count=int(streams[0]["nb_read_frames"])
    pixels=frame_gray(video,w,h,count)
    frames=scene["frames"]
    if len(frames)!=7 or [x["tick"] for x in frames]!=[0,12,24,36,48,60,71]:
        raise ValueError("SAMPLED_FRAME_CLOCK_MISMATCH")
    rows=[];worst=0;coverage=[]
    for sample in frames:
        t=sample["tick"]
        if t>=count or len(sample["mesh_points"])!=112:
            raise ValueError("FRAME_TO_MESH_COVERAGE")
        projected=[];ids=set()
        for pt in sample["mesh_points"]:
            label=(pt["actor"],pt["vertex"])
            if label in ids or pt["actor"] not in ("CobaltOriginal","MarigoldOriginal") or not 0<=pt["vertex"]<56:
                raise ValueError("SOURCE_VERTEX_ID_DUPLICATE_OR_MISSING")
            ids.add(label)
            u,v,depth=project(pt["world_xyz"],cam)
            err=math.hypot(u-pt["native_xy"][0],v-pt["native_xy"][1])
            worst=max(worst,err)
            if err>1e-4:
                raise ValueError("INDEPENDENT_CAMERA_NATIVE_PROJECTION_DISAGREEMENT")
            if 0<=u<=1 and 0<=v<=1 and depth>0:
                projected.append((round(u*(w-1)),round((1-v)*(h-1))))
        if len(ids)!=112:
            raise ValueError("INCOMPLETE_INDEXED_SOURCE_MESH")
        image=pixels[t]
        lit=[(i%w,i//w) for i,value in enumerate(image) if value>24]
        if not lit:
            rows.append({"tick":t,"status":"UNKNOWN_NO_FOREGROUND_PIXELS","foreground_pixels":0,
                         "source_projected_vertices":len(projected)})
            continue
        supported=0
        for x,y in projected:
            found=False
            for yy in range(max(0,y-4),min(h,y+5)):
                for xx in range(max(0,x-4),min(w,x+5)):
                    if image[yy*w+xx]>24:
                        found=True;break
                if found:break
            supported+=found
        coverage.append(supported/max(1,len(projected)))
        rows.append({"tick":t,"status":"OBSERVED_NOT_ANATOMY_ACCEPTED",
                     "foreground_pixels":len(lit),
                     "foreground_bbox":bbox(lit),
                     "projected_source_bbox":bbox(projected),
                     "in_view_source_vertices":len(projected),
                     "source_vertices_with_visible_pixel_nearby":supported,
                     "projected_vertex_pixel_support_fraction":round(supported/max(1,len(projected)),4)})
    receipt={"schema":"scp.visualqa.w2b_image_geometry.v1",
             "status":"OBSERVED_UNQUALIFIED" if len(coverage)==len(frames) else "UNKNOWN_MISSING_FOREGROUND",
             "video_sha256":sha(video),"scene_sha256":sha(manifest),
             "native_receipt_sha256":sha(native),
             "independent_camera_vs_native_max_uv_error":worst,
             "frames":rows,"minimum_observed_source_vertex_pixel_support":min(coverage,default=None),
             "anatomical_quality":"UNKNOWN_NO_SOURCE_APPROVED_ANATOMY",
             "occlusion_skin_contact":"UNKNOWN_NOT_QUALIFIED",
             "release_acceptance":"NOT_ACCEPTED_RESEARCH_ONLY"}
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":receipt["status"],"camera_error":worst,
                      "min_pixel_support":receipt["minimum_observed_source_vertex_pixel_support"]}))
    return receipt


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for field in ("manifest","video","native","out"):
        p.add_argument("--"+field,required=True)
    a=p.parse_args()
    verify(a.manifest,a.video,a.native,a.out)
