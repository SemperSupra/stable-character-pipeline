"""N03D-BG: REAL original CC0 MPFB matched-body two-rig worn shoe H.264 diagnostic.

True in-memory authored pose tracks 72x12fps from SAME exact original 100STYLE
360x60Hz source, on 2 paired Aster/Juniper identical bodies standard163
and game_engine53 with real licensed skinned shoes. Two cameras. Not a
human-independent visual *quality* acceptance; video format and native source
image provenance can be independently inspected, but physical gait remains HOLD.
"""
import argparse,hashlib,importlib.util,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector,Quaternion

HERE=Path(__file__).parent
bf_file=HERE.parent/"n03d-bf-real-morph-shoes"/"native_shoe.py"
spec=importlib.util.spec_from_file_location("n03d_bf_source_safe_video_builder",str(bf_file))
bf=importlib.util.module_from_spec(spec)
spec.loader.exec_module(bf)
be=bf.be
def need(c,reason):
    if not c:raise ValueError(reason)
def sha(data):return hashlib.sha256(data).hexdigest()
def mat(name,rgba):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=tuple(rgba)
    node=m.node_tree.nodes.get("Principled BSDF")
    if node:
        node.inputs["Base Color"].default_value=tuple(rgba)
        node.inputs["Roughness"].default_value=.80
    return m
def decorate(a):
    from mathutils import Vector
    placements={
      "AsterOriginal:default":(-3.3,"Aster - 163"),
      "AsterOriginal:game_engine":(-1.10,"Aster - 53"),
      "JuniperOriginal:default":(1.1,"Juniper - 163"),
      "JuniperOriginal:game_engine":(3.3,"Juniper - 53")
    }
    for actor in a:
        for rig_name,item in actor["versions"].items():
            ident=actor["actor"]+":"+rig_name
            color=((.32,.48,.72,1.) if rig_name=="default" else (.76,.61,.38,1.))
            body=item["body"];shoe=item["shoe"]
            body.data.materials.clear();body.data.materials.append(mat(ident+"_Skin",color))
            shoe.data.materials.clear()
            shoe.data.materials.append(mat(ident+"_Shoes",(.21,.23,.26,1.)))
            x,label=placements[ident]
            t=bpy.data.curves.new(ident+"_ID","FONT")
            t.body=label;t.align_x="CENTER";t.size=.19
            obj=bpy.data.objects.new(t.name,t);bpy.context.collection.objects.link(obj)
            obj.location=(x,-.55,2.14);obj.rotation_euler=(math.pi/2,0,0)
            obj.data.materials.append(mat(ident+"_Label",(0.15,.16,.18,1)))
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,-.02))
    floor=bpy.context.object;floor.name="N03D_BG_OriginalFlatParkReferenceZ0"
    floor.dimensions=(12.2,3.8,.04)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    floor.data.materials.append(mat("N03D_BG_Floor",(.75,.79,.72,1.)))
    return placements
def camera(name,location):
    camera=bpy.data.cameras.new(name)
    ob=bpy.data.objects.new(name,camera);bpy.context.collection.objects.link(ob)
    ob.location=location
    ob.rotation_euler=(Vector((0,0,1.18))-ob.location).to_track_quat("-Z","Y").to_euler()
    camera.type="ORTHO";camera.ortho_scale=11.5
    return ob
def encode_gait(actors,nodes,bvh,placements):
    """Author real keyframed independent rig source at exact 60->12Hz times.
    No interpolated invented bone poses; only frame 120+5*k is keyed.
    """
    import math
    basis=Matrix.Rotation(math.pi/2,3,"X")
    source_length=(Vector(nodes["LeftKnee"]["offset"]).length+
                   Vector(nodes["LeftAnkle"]["offset"]).length)*.01
    root0=bf.source_pos(nodes["Hips"],bvh["frames"][120])
    receipts=[]
    for actor in actors:
        for rig_name,item in actor["versions"].items():
            rig=item["rig"]
            key=actor["actor"]+":"+rig_name
            x,_=placements[key]
            mapping=be.MAP[rig_name]
            need(all(name in rig.pose.bones for name in mapping.values()),
                 "NATIVE_SOURCE_RIG_BONE_LOST")
            ratio=(rig.data.bones[mapping["LeftHip"]].length+
                   rig.data.bones[mapping["LeftKnee"]].length)/source_length
            need(.2<ratio<2,"CROSS_RIG_MATCHED_MORPH_SCALE")
            origin=rig.matrix_world.copy()
            for bone in rig.pose.bones:
                bone.rotation_mode="QUATERNION"
                bone.rotation_quaternion=Quaternion((1,0,0,0))
                bone.location=(0,0,0)
            for i in range(72):
                source=bvh["frames"][120+5*i]
                for src,target in mapping.items():
                    pb=rig.pose.bones[target]
                    q=basis@bf.source_rotation(nodes[src],source)@basis.inverted()
                    rest=pb.bone.matrix_local.to_3x3()
                    if pb.bone.parent:
                        rest=pb.bone.parent.matrix_local.to_3x3().inverted()@rest
                    q=rest.inverted()@q@rest
                    pb.rotation_quaternion=q.to_quaternion()
                    pb.keyframe_insert("rotation_quaternion",frame=i)
                path=basis@(bf.source_pos(nodes["Hips"],source)-root0)
                offset=Vector((x,0,0))+path*.01*ratio
                rig.matrix_world=Matrix.Translation(offset)@origin
                rig.keyframe_insert("location",frame=i)
            receipts.append({"actor":actor["actor"],"rig":rig_name,"bones":item["count"],
                             "original_actor_identity":True,
                             "same_morphology_19158_vertex_delta_m":actor["shape"]["max_rest_vertex_deviation_m"],
                             "actual_CC0_shoes":item["shoe_source_asset"],
                             "source_frames":[120,475],"root_scale_leg_ratio":round(ratio,6),
                             "true_physical_gait_accepted":False})
    return receipts
def native_witness(actors):
    scene=bpy.context.scene;out=[]
    for frame in (0,35,71):
        scene.frame_set(frame);bpy.context.view_layer.update()
        actors_out=[]
        for a in actors:
            for rig_name,v in a["versions"].items():
                shoe=v["shoe"]
                ev=shoe.evaluated_get(bpy.context.evaluated_depsgraph_get())
                mesh=ev.to_mesh()
                try:
                    points=[ev.matrix_world@p.co for p in mesh.vertices]
                    need(len(points)>=100,"ACTUAL_WORN_SHOE_GONE")
                    lo=min(float(p.z) for p in points)
                finally:ev.to_mesh_clear()
                actors_out.append({"actor":a["actor"],"rig":rig_name,
                                   "actual_shoe_evaluated_vertices":len(points),
                                   "shoe_global_min_z_m":round(lo,6)})
        out.append({"native_frame":frame,"source_frame":120+5*frame,
                    "actor_observations":actors_out})
    return out
def main():
    arg=argparse.ArgumentParser()
    for k in ("source","motion","shoe-archive","work","out"):arg.add_argument("--"+k,required=True)
    args=arg.parse_args(sys.argv[sys.argv.index("--")+1:])
    m=Path(args.motion).read_bytes()
    need(bf.git_blob_sha(m)==bf.SOURCE_BLOB,"AUTHENTIC_100STYLE_SHA")
    bvh=bf.parse_bvh(m)
    need(bvh["count"]==2400 and abs(bvh["frame_time"]-1/60)<1e-5,"SAME_SOURCE_CLOCK")
    needs=Path(args.shoe_archive).read_bytes()
    need(sha(needs)==bf.SHOE_SHA,"AUTHENTIC_CC0_WORN_SHOE")
    pack=bf.wardrobe.source_archive("shoes01",needs)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    hs,ts,props=be.services()
    actors=be.build_pair(hs,ts,props)
    bf.shoe_asset(pack,actors,args.work,hs)
    placements=decorate(actors)
    nodes={a["name"]:a for a in bvh["nodes"] if not a["end"]}
    receipt=encode_gait(actors,nodes,bvh,placements)
    scene=bpy.context.scene
    scene.frame_start=0;scene.frame_end=71;scene.render.fps=12
    scene.render.engine="BLENDER_WORKBENCH"
    scene.render.resolution_x=384;scene.render.resolution_y=216
    scene.render.resolution_percentage=100
    scene.display.shading.light="STUDIO"
    scene.display.shading.color_type="MATERIAL"
    scene.view_settings.view_transform="Standard"
    scene.render.image_settings.file_format="FFMPEG"
    scene.render.ffmpeg.format="MPEG4"
    scene.render.ffmpeg.codec="H264"
    scene.render.ffmpeg.audio_codec="NONE"
    scene.render.ffmpeg.constant_rate_factor="MEDIUM"
    cams=[camera("N03D_BG_Front",(0,-11.5,2.95)),
          camera("N03D_BG_Oblique",(4.5,-10.5,3.0))]
    evidence=native_witness(actors)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    media=[]
    for cam in cams:
        scene.camera=cam
        name=cam.name.lower().replace("n03d_bg_","")
        scene.render.filepath=str(out/(name+"_"))
        bpy.ops.render.render(animation=True)
        videos=list(out.glob(name+"_*.mp4"))
        need(len(videos)==1 and videos[0].stat().st_size>10000,"NO_REAL_H264_"+name)
        media.append({"camera":name,"file":videos[0].name,
                      "sha256":sha(videos[0].read_bytes()),"bytes":videos[0].stat().st_size,
                      "source_rights_attribution":"MakeHuman CC0 + Ian Mason 100STYLE CC BY4",
                      "mvp_accepted":False})
    report={"schema":"scp.n03d-bg.two-camera-source-safe-visual-witness.v1",
            "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
            "source_MPF_upstream":be.c.UPSTREAM,
            "source_bvh_blob":bf.SOURCE_BLOB,
            "source_bvh_sha256":sha(m),
            "shoes01_CC0_archive_sha256":bf.SHOE_SHA,
            "official_blender":list(bpy.app.version),
            "native_scene_h264_12fps_frames":72,
            "actual_separate_source_original_actors":receipt,
            "native_source_to_shoe_observations":evidence,
            "videos":media,
            "visual_full_biomechanics_verified":False,
            "user_protected_Naomi_Alison_used":False,
            "physical_gait_accepted":False,"mvp_accepted":False,
            "status":"PASS_NARROW_AUTHENTIC_2_CAMERA_FILM_HOLD_VISUAL_QUALITY"}
    (out/"n03d-bg-video-witness.json").write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n")
    (out/"ATTRIBUTION.txt").write_text("Synthetic original MakeHuman/MPFB CC0 characters/shoes; 100STYLE Neutral_FW gait motion (c) Ian Mason and coauthors under Creative Commons Attribution 4.0. Source: https://www.ianxmason.com/100style/ . This diagnostic is not Naomi/Alison and is not a physically accepted film.\n")
    print("N03D_BG_REAL_TWO_CAMERA_ORIGINAL_H264_FILMS",
          json.dumps({"source_sha":sha(m),"actors":receipt,"videos":media,"status":report["status"]},sort_keys=True),flush=True)
if __name__=="__main__":main()
