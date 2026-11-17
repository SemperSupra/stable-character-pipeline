#!/usr/bin/env python3
"""Original-synthetic R077 full native 72-frame Blender replay. Not film MVP acceptance."""
import argparse,hashlib,json,math,sys
from pathlib import Path
def demand(ok,why):
    if not ok:raise RuntimeError(why)
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def check_frames(rows):
    demand(len(rows)==72,"FRAME_COUNT_NOT_72")
    hashes=[]
    for i,row in enumerate(rows):
        demand(type(row) is dict and row.get("frame")==i,"FRAME_ORDER_OR_OMISSION")
        h=row.get("sha256")
        demand(isinstance(h,str) and len(h)==64 and all(x in "0123456789abcdef" for x in h),"FRAME_HASH_INVALID")
        hashes.append(h)
    demand(len(set(hashes))>=3 and hashes[0]!=hashes[-1],"STATIC_OR_UNCHANGING_FRAMES")
    return len(set(hashes))
def run(a):
    # Validate source input before importing Blender; source-only preflight and
    # negative tests run on CPUs without bpy and must not depend on engine IO.
    saved=Path(a.saved)
    demand(saved.is_file() and digest(saved)==a.saved_sha,"SOURCE_SAVED_BLEND_SHA_MISMATCH")
    import bpy
    from mathutils import Vector
    bpy.ops.wm.open_mainfile(filepath=str(saved.resolve()),load_ui=False,use_scripts=False)
    demand(digest(saved)==a.saved_sha,"SAVED_BLEND_CHANGED_ON_REOPEN")
    scene=bpy.context.scene
    demand((scene.frame_start,scene.frame_end,scene.render.fps)==(0,71,12),"SOURCE_CLOCK_MISMATCH")
    demand(scene.camera is not None,"NATIVE_CAMERA_MISSING")
    arms=[x for x in bpy.data.objects if x.type=="ARMATURE"]
    demand(len(arms)==2 and all(len(x.data.bones)>=17 for x in arms),"TWO_ACTOR_RIG_MISSING")
    skinned=[x for x in bpy.data.objects if x.type=="MESH" and any(
        m.type=="ARMATURE" and m.object in arms for m in x.modifiers)]
    demand(len(skinned)>=2,"SOURCE_NATIVE_SKIN_MISSING")
    floor=bpy.data.objects.get("R074_OriginalPathGround")
    demand(floor is not None and floor.type=="MESH","NATIVE_FLOOR_SOURCE_MISSING")
    z=max((floor.matrix_world @ Vector(c)).z for c in floor.bound_box)
    demand(math.isfinite(z) and abs(z)<=1e-5,"NATIVE_SOURCE_FLOOR_CHANGED")
    framepath=Path(a.frames)
    demand(not framepath.exists(),"FRAME_DIRECTORY_EXISTS")
    framepath.mkdir(parents=True)
    scene.render.engine="BLENDER_WORKBENCH"
    scene.render.resolution_x=320
    scene.render.resolution_y=180
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    rows=[]
    for i in range(72):
        scene.frame_set(i)
        target=framepath/("frame_%03d.png"%i)
        demand(not target.exists(),"REFUSE_FRAME_OVERWRITE")
        scene.render.filepath=str(target)
        bpy.ops.render.render(write_still=True)
        demand(target.is_file() and target.stat().st_size>100,"NATIVE_FRAME_MISSING")
        rows.append({"frame":i,"sha256":digest(target),"bytes":target.stat().st_size})
    unique=check_frames(rows)
    result={"schema":"scp.r077.r009-original-native-72-frame.v1",
       "status":"HOLD_NATIVE_GAIT_CONTACT_AND_REAL_CHARACTER_RIGHTS",
       "source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
       "source_glb_sha256":a.glb_sha,"saved_blend_sha256":a.saved_sha,
       "loaded_with_scripts_disabled":True,
       "blender_version":bpy.app.version_string,
       "actual_rendered_frame_count":72,
       "native_source_fps":12,"render_resolution":[320,180],
       "unique_frame_sha256_count":unique,"frames":rows,
       "h264_encoded":False,"contact_accepted":False,
       "natural_gait_accepted":False,"mvp_accepted":False,"release_authorized":False}
    out=Path(a.out)
    demand(not out.exists(),"REFUSE_RECEIPT_OVERWRITE")
    out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf8")
    print("R077_B_NATIVE_72_FRAMES_SOURCE_ONLY_HOLD",unique,a.saved_sha)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("saved","saved-sha","glb-sha","frames","out"):p.add_argument("--"+name,required=True)
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    a=p.parse_args(argv)
    demand(len(a.saved_sha)==64 and len(a.glb_sha)==64,"SHA_REQUIRED")
    run(a)
if __name__=="__main__":
    try:main()
    except (OSError,RuntimeError) as err:
        print("R077_B_HOLD",str(err),file=sys.stderr)
        sys.exit(12)
