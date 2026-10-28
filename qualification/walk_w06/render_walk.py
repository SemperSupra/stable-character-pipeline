"""W06 public original-character native evaluated Blender mesh video.
Native Blender object evaluation, not skin-weight deformation or private characters.
"""
import hashlib,json,subprocess,sys
from pathlib import Path
import bpy
from PIL import Image,ImageDraw
import imageio_ffmpeg
from gait import validate
from source_native import build,polygons

W,H=960,540
def hull(points):
    pts=sorted(set((round(x,3),round(y,3)) for x,y in points))
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[];upper=[]
    for p in pts:
        while len(lower)>1 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper)>1 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
        upper.append(p)
    result=lower[:-1]+upper[:-1]
    if len(result)<3:raise ValueError("NATIVE_HULL_EMPTY")
    return result

def background(frame):
    image=Image.new("RGB",(W,H),(225,241,251))
    d=ImageDraw.Draw(image)
    ground=round(H-.15/3*H)
    d.rectangle((0,ground,W,H),fill=(138,187,135))
    d.ellipse((-100,ground+2,W+100,H+150),fill=(211,188,149))
    for x,y,r in ((92,142,40),(178,163,31),(787,135,42),(887,169,35)):
        d.rectangle((x-8,y+15,x+8,ground),fill=(122,102,72))
        d.ellipse((x-r,y-r,x+r,y+r),fill=(87,151,105))
    d.text((20,18),"W06 ORIGINAL PUBLIC WALKERS / NATIVE BLENDER",fill=(31,75,96))
    d.text((20,38),"Procedural 2D gait / Native evaluated objects / Not real people",fill=(54,98,103))
    d.text((20,H-25),"FRAME %02d/72 | %.2fs"%(frame+1,frame/12),fill=(45,80,54))
    return image

def run(source_file,outdir):
    source=Path(source_file)
    source_bytes=source.read_bytes()
    motion=json.loads(source_bytes)
    validated=validate(motion)
    out=Path(outdir)
    out.mkdir(parents=True,exist_ok=True)
    blend=out/"two_original_public_walkers.blend"
    actors=build(motion,blend)
    for parts in actors.values():
        for object,color,order in parts.values():
            mat=bpy.data.materials.new("W06_"+object.name)
            mat.diffuse_color=tuple(int(color[i:i+2],16)/255 for i in (1,3,5))+(1.0,)
            object.data.materials.clear()
            object.data.materials.append(mat)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
    if not blend.exists() or blend.stat().st_size<10000:raise RuntimeError("MISSING_EDITABLE_BLEND")
    frame_dir=out/"frames";frame_dir.mkdir(exist_ok=True)
    observations=[]
    for f in motion["frames"]:
        i=f["index"]
        image=background(i);canvas=ImageDraw.Draw(image)
        seen={}
        data=polygons(actors,i,W,H)
        for actor in motion["actors"]:
            aid=actor["id"]
            outline=[]
            for color,verts in data[aid]:
                shape=hull(verts)
                canvas.polygon(shape,fill=color)
                outline.extend(shape)
            if not outline:raise RuntimeError("NO_NATIVE_EVALUATED_ACTOR_GEOMETRY")
            bounds=[round(min(p[0] for p in outline),3),
                    round(min(p[1] for p in outline),3),
                    round(max(p[0] for p in outline),3),
                    round(max(p[1] for p in outline),3)]
            seen[aid]={"bbox_pixels":bounds,
                      "root_source_x":f["actors"][aid]["root_x"],
                      "foot_contacts":f["actors"][aid]["contact"]}
        filename=frame_dir/("frame_%03d.png"%i)
        image.save(filename)
        if i in (0,18,36,54,71):
            (out/("preview_%03d.png"%i)).write_bytes(filename.read_bytes())
        observations.append({"frame":i,"timestamp_ms":f["timestamp_ms"],"actors":seen})
    if len(observations)!=72:raise RuntimeError("NATIVE_WITNESS_FRAME_MISMATCH")
    for actor in motion["actors"]:
        aid=actor["id"]
        start=observations[0]["actors"][aid]["bbox_pixels"][0]
        end=observations[-1]["actors"][aid]["bbox_pixels"][0]
        if abs(start-end)<100:raise RuntimeError("STATIC_NATIVE_CHARACTER_FALSE_PASS")
    video=out/"two_original_public_walkers_native.mp4"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),"-hide_banner","-loglevel","error",
                    "-nostdin","-y","-framerate","12","-start_number","0","-i",
                    str(frame_dir/"frame_%03d.png"),"-c:v","libx264",
                    "-pix_fmt","yuv420p","-movflags","+faststart",str(video)],
                   check=True,timeout=120)
    if video.stat().st_size<25000:raise RuntimeError("EMPTY_NATIVE_VIDEO")
    digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    receipt={"schema":"scp.walk_w06_native_evaluated_mesh.v1",
             "status":"PASS_ORIGINAL_NATIVE_OBJECT_EVALUATION_AND_H264",
             "source_motion_sha256":digest(source),
             "blender_sha256":digest(blend),"video_sha256":digest(video),
             "source_rights":motion["source_rights"],
             "frame_count":72,"fps":12,"duration_seconds":6,
             "native_blender_evaluated_mesh":True,
             "native_cycles_rendered":False,
             "weighted_skin_deformation":"NOT_MEASURED",
             "natural_human_gait":"NOT_TESTED",
             "original_private_subjects":"NOT_USED",
             "source_contact_invariants":validated,
             "frame_observations":observations}
    (out/"native_mesh_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print("W06_NATIVE_TWO_ORIGINAL_WALKERS_PASS",json.dumps({k:v for k,v in receipt.items() if k!="frame_observations"},sort_keys=True))
if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: render_walk.py MOTION_JSON OUT_DIR")
    run(sys.argv[1],sys.argv[2])
