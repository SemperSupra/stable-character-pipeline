"""W8A: source-original animated rigid upper-body proxy + real Blender two-view video.

These are opaque authored proxy solids, NOT approved anatomical full body,
true weighted torso/arms, or a passing human visual model.
"""
import argparse,hashlib,json,math,subprocess
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
ACTORS=("CobaltOriginal","MarigoldOriginal")
def add_part(arm,name,kind,location,scale,color):
    if kind=="sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,location=location)
    else:
        bpy.ops.mesh.primitive_cube_add(size=1,location=location)
    obj=bpy.context.object
    obj.name=arm.name+"_"+name
    obj.parent=arm
    obj.location=location
    obj.scale=scale
    obj.color=color
    obj["source_rights"]=RIGHTS
    obj["visual_role"]=name
    return obj

def add_body(arm,actor):
    if actor not in ACTORS or arm.get("source_rights")!=RIGHTS:
        raise ValueError("MODEL_RIGHTS_OR_ACTOR")
    c=(.12,.45,.8,1) if actor==ACTORS[0] else (.85,.33,.19,1)
    parts=[]
    for name,kind,loc,scale in (
        ("Pelvis","cube",(0,0,1.09),(.48,.30,.24)),
        ("Torso","cube",(0,0,1.50),(.43,.30,.73)),
        ("Neck","cube",(0,0,1.93),(.15,.16,.18)),
        ("Head","sphere",(0,0,2.17),(.19,.17,.23)),
        ("LeftArm","cube",(-.34,0,1.61),(.18,.21,.65)),
        ("RightArm","cube",(.34,0,1.61),(.18,.21,.65)),
        ("LeftHand","sphere",(-.34,0,1.23),(.08,.09,.10)),
        ("RightHand","sphere",(.34,0,1.23),(.08,.09,.10))):
        parts.append(add_part(arm,name,kind,loc,scale,c))
    return parts


def add_articulated_upper_proxy(arm, actor, parts, original_source):
    """Actual keyed original RIGID upper-arm and hand motion; never a skinned human."""
    source_actor = next((a for a in original_source["actors"] if a.get("id")==actor), None)
    if source_actor is None or len(source_actor.get("frames",[]))!=24:
        raise ValueError("W8_SOURCE_ACTOR_FRAMES_MISSING")
    owned = {o.get("visual_role"):o for o in parts}
    for name in ("LeftArm","RightArm","LeftHand","RightHand","Torso","Head"):
        if name not in owned or owned[name].get("source_rights")!=RIGHTS:
            raise ValueError("W8_UPPER_BODY_PART_RIGHTS")
    recorded = []
    for t in range(24):
        f=source_actor["frames"][t]
        if f.get("index")!=t or f.get("time_num")!=t or f.get("time_den")!=12:
            raise ValueError("W8_SOURCE_FRAME_CLOCK")
        phase=2*math.pi*t/12
        one={"frame":t}
        for side,sign in (("Left",1),("Right",-1)):
            angle=.28*math.sin(phase)*sign
            arm_obj=owned[side+"Arm"]
            arm_obj.rotation_mode="XYZ"
            arm_obj.rotation_euler.x=angle
            arm_obj.keyframe_insert(data_path="rotation_euler",frame=t)
            hand_obj=owned[side+"Hand"]
            hand_obj.location.y=.20*math.sin(phase)*sign
            hand_obj.keyframe_insert(data_path="location",frame=t)
            one[side]={"upper_arm_x_rad":angle,"hand_local_y":hand_obj.location.y,
                       "source_motion":"SELF_AUTHORED_PERIODIC_UPPER_PROXY_NO_BIOLOGICAL_PRIOR"}
        recorded.append(one)
    return recorded

def camera(name,loc,target):
    camera=bpy.data.cameras.new(name)
    obj=bpy.data.objects.new(name,camera)
    bpy.context.scene.collection.objects.link(obj)
    obj.location=loc
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()
    camera.type="ORTHO";camera.ortho_scale=5.75
    return obj

def ffmpeg(argv):
    p=subprocess.run(argv,check=False,capture_output=True,text=True,timeout=180)
    if p.returncode:
        raise ValueError("NATIVE_FFMPEG_FAILED_"+p.stderr[-250:])
    return p

def run(source,out):
    source,out=Path(source),Path(out)
    out.mkdir(parents=True,exist_ok=True)
    receipt=json.loads((source/"source_motion_receipt.json").read_text())
    blend=source/"original_source_grounded_24frame_native.blend"
    sourcejson=source/"source.json"
    if receipt.get("schema")!="scp.walk_w5d_native_grounded.v1" or receipt.get("rights")!=RIGHTS or receipt.get("frame_count")!=24:
        raise ValueError("W5D_SOURCE_NOT_QUALIFIED")
    if hashlib.sha256(blend.read_bytes()).hexdigest()!=receipt["blend_sha256"] or hashlib.sha256(sourcejson.read_bytes()).hexdigest()!=receipt["source_sha256"]:
        raise ValueError("SOURCE_MODEL_SHA_MISMATCH")
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    scene=bpy.context.scene
    scene.frame_start=0;scene.frame_end=23;scene.render.fps=12
    original_source=json.loads(sourcejson.read_text())
    if original_source.get("schema")!="scp.walk_w7a_original_approach.v1" or original_source.get("rights")!=RIGHTS:
        raise ValueError("W8_UNADMITTED_ORIGINAL_SOURCE")
    rigs=[]
    meshes=[]
    articulated=[]
    for actor in ACTORS:
        rig=bpy.data.objects.get(actor+"_Skeleton")
        skin=bpy.data.objects.get(actor+"_SkinnedMesh")
        if rig is None or skin is None or rig.type!="ARMATURE" or skin.type!="MESH" or len(rig.pose.bones)!=6:
            raise ValueError("NATIVE_SOURCE_RIG_ID_OR_SKIN")
        if len(skin.data.vertices)!=48 or rig.get("source_rights")!=RIGHTS:
            raise ValueError("NATIVE_SKIN_OR_RIGHTS")
        rigs.append(rig)
        parts=add_body(rig,actor)
        meshes.extend(parts)
        articulated.append({"actor":actor,"keyframes":add_articulated_upper_proxy(rig,actor,parts,original_source)})
        skin.color=(.12,.45,.80,1) if actor==ACTORS[0] else (.85,.33,.19,1)
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,-.105))
    floor=bpy.context.object;floor.name="OriginalSourceFloor"
    floor.scale=(12,12,.18);floor.color=(.77,.78,.78,1)
    cameras=[
        camera("OriginalFront",(0,-8.5,2.8),(0,0,1.15)),
        camera("OriginalOblique",(7.5,-7,3.1),(0,0,1.15))
    ]
    scene.render.engine="BLENDER_WORKBENCH"
    scene.display.shading.light="STUDIO"
    scene.display.shading.color_type="OBJECT"
    scene.display.shading.show_shadows=True
    scene.render.resolution_x=640;scene.render.resolution_y=360;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.film_transparent=False
    scene.frame_set(0)
    bpy.context.view_layer.update()  # resolve camera matrix_world after assigning location/rotation
    original_sha=hashlib.sha256(blend.read_bytes()).hexdigest()
    outputs=[]
    for cam in cameras:
        scene.camera=cam
        location_probes=[]
        for actor in ACTORS:
            rig=bpy.data.objects.get(actor+"_Skeleton")
            for role,height in (("Head",2.17),("Torso",1.5),("Pelvis",1.09)):
                projected=world_to_camera_view(scene,cam,rig.matrix_world@Vector((0,0,height)))
                if not (0<projected.x<1 and 0<projected.y<1 and projected.z>0):
                    raise ValueError(f"CORE_BODY_OUT_OF_CAMERA_VIEW_{cam.name}_{actor}_{role}_{float(projected.x):.3f}_{float(projected.y):.3f}_{float(projected.z):.3f}")
                location_probes.append({"actor":actor,"part":role,"uv":[float(projected.x),float(projected.y)]})
        frames=out/cam.name;frames.mkdir(exist_ok=True)
        for tick in range(24):
            scene.frame_set(tick)
            scene.render.filepath=str((frames/f"frame_{tick:03}.png").resolve())
            bpy.ops.render.render(write_still=True)
            if not (frames/f"frame_{tick:03}.png").is_file():
                raise ValueError("NATIVE_FRAME_NOT_RENDERED")
        video=out/(cam.name+".mp4")
        ffmpeg(["ffmpeg","-nostdin","-y","-v","error","-framerate","12",
                "-i",str(frames/"frame_%03d.png"),"-c:v","libx264",
                "-pix_fmt","yuv420p","-r","12",str(video)])
        if video.stat().st_size<1024:
            raise ValueError("ENCODED_H264_VIDEO_NOT_ADMITTED")
        outputs.append({"camera":cam.name,"video":video.name,
                        "video_sha256":hashlib.sha256(video.read_bytes()).hexdigest(),
                        "frame_count":24,"core_body_camera_projection":location_probes})
    # Independent Blender evaluated local object animation witness (source state,
    # not a pixel perceptual oracle). Reject static or wrong-bound original arms.
    upper_observed=[]
    for t in range(24):
        scene.frame_set(t)
        frame={"frame":t,"actors":[]}
        for actor in ACTORS:
            rig=bpy.data.objects[actor+"_Skeleton"]
            arms=[]
            for side,sign in (("Left",1),("Right",-1)):
                obj=bpy.data.objects.get(rig.name+"_"+side+"Arm")
                hand=bpy.data.objects.get(rig.name+"_"+side+"Hand")
                if obj is None or hand is None:
                    raise ValueError("W8_ACTUAL_ARM_OR_HAND_MISSING")
                target=.28*math.sin(2*math.pi*t/12)*sign
                if abs(float(obj.rotation_euler.x)-target)>1e-5:
                    raise ValueError("W8_ACTUAL_BLENDER_ARM_ANGLE_MISMATCH")
                if abs(float(hand.location.y)-.20*math.sin(2*math.pi*t/12)*sign)>1e-5:
                    raise ValueError("W8_ACTUAL_BLENDER_HAND_MOTION_MISMATCH")
                arms.append({"side":side,"upper_arm_x_rad":float(obj.rotation_euler.x),
                             "hand_local_y":float(hand.location.y)})
            frame["actors"].append({"id":actor,"arms":arms})
        upper_observed.append(frame)
    if abs(upper_observed[3]["actors"][0]["arms"][0]["upper_arm_x_rad"])<.2:
        raise ValueError("W8_RIGID_UPPER_BODY_STILL_STATIC")
    upper_file=out/"observed_blender_upper_arm_24frame.json"
    upper_file.write_text(json.dumps({"schema":"scp.walk_w8a_observed_upper_proxy.v1",
       "source_motion_sha256":receipt["source_sha256"],
       "original_blend_sha256":original_sha,"frames":upper_observed},sort_keys=True,indent=2)+"\n")
    if hashlib.sha256(blend.read_bytes()).hexdigest()!=original_sha:
        raise ValueError("ORIGINAL_W5D_MODEL_MUTATED")
    report={"schema":"scp.walk_w6a_proxy_multiview.v1",
            "status":"PASS_NATIVE_ORIGINAL_MANNEQUIN_RENDER_ONLY",
            "rights":RIGHTS,"original_w5d_blend_sha256":original_sha,
            "source_motion_sha256":receipt["source_sha256"],
            "profile":receipt["profile"],"cameras":outputs,
            "head_torso_arms":"VISIBLE_ANIMATED_RIGID_ARMS_HEAD_TORSO_PROXY_NOT_ANATOMICAL",
            "W8_arm_motion":"ACTUAL_KEYED_RIGID_UPPER_PROXY_24FRAME",
            "W8_arm_witness_file":"observed_blender_upper_arm_24frame.json",
            "natural_human_behavior":"UNKNOWN_NO_INDEPENDENT_NORMATIVE_MODEL",
            "torso_arm_skinning":"NOT_DEFORM_RIGGED",
            "physical_rom":"UNKNOWN_NO_HUMAN_ANATOMY",
            "real_person":"NONE_SOURCE_ORIGINAL",
            "L1_pixel_acceptance":"SEPARATE_DECODER_RECEIPT_REQUIRED",
            "multi_camera_geom":"ONLY_PROJECTED_CORE_NOT_OCCLUSION"}
    (out/"native_render_receipt.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("W6A_NATIVE_ORIGINAL_PROXY_MULTIVIEW",json.dumps(report,sort_keys=True))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();run(a.source,a.out)
