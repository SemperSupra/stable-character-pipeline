"""N03D-BH 360 native 60Hz original MakeHuman foot-body material heel/ball region
and source-safe multi-view Blender true raster witnesses. Not shoe or true stance.
"""
import argparse,hashlib,json,math,statistics,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"n03d-be-morph-controlled"))
sys.path.insert(0,str(HERE.parent/"n03d-bd-matched-rig"))
sys.path.insert(0,str(HERE.parent/"r078-r009-mpfb-pair"))
sys.path.insert(0,str(HERE.parent/"r088-motion-real"))
import morph_matched as be
import native as bd
import contract
from bvh_preflight import parse_bvh,git_blob_sha

SOURCE_BLOB="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61"
def need(ok,msg):
    if not ok:raise ValueError(msg)
def original_material_ids(body,rig,mapping):
    out={}
    evalobj=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evalobj.to_mesh()
    try:
        need(len(mesh.vertices)==len(body.data.vertices),"SOURCE_MASKED_TOPOLOGY")
        names={g.name:g.index for g in body.vertex_groups}
        for side in ("L","R"):
            an=mapping["LeftAnkle" if side=="L" else "RightAnkle"]
            toe=mapping["LeftToe" if side=="L" else "RightToe"]
            need(an in names and toe in names,"NAMED_SOURCE_FOOT_SKIN_MISSING")
            group={names[an],names[toe]}
            candidates=[i for i,v in enumerate(body.data.vertices)
                        if sum(g.weight for g in v.groups if g.group in group)>=.40]
            need(len(candidates)>=25,"INSUFFICIENT_BODY_FOOT_SKIN")
            direction=(rig.matrix_world@rig.data.bones[toe].head_local-
                       rig.matrix_world@rig.data.bones[an].head_local)
            direction.z=0
            need(direction.length>.025,"SOURCE_FOOT_AXIS_UNIDENTIFIABLE")
            direction.normalize()
            items=sorted([(float((evalobj.matrix_world@mesh.vertices[i].co).z),i)
                           for i in candidates])
            low=[i for _,i in items[:max(20,int(.3*len(items)))]]
            along=sorted([(float((evalobj.matrix_world@mesh.vertices[i].co).dot(direction)),i)
                          for i in low])
            n=max(5,int(.25*len(along)))
            need(2*n<=len(along),"FOOT_HEEL_BALL_PARTITION_COLLAPSE")
            out[side]={"heel_region_fixed_vertex_ids":[i for q,i in along[:n]],
                       "ball_region_fixed_vertex_ids":[i for q,i in along[-n:]],
                       "selected_source_weighted_vertices":len(candidates),
                       "lower_rest_region_vertices":len(low),
                       "rest_toe_axis":[round(float(z),6) for z in direction]}
        return out
    finally:evalobj.to_mesh_clear()
def observe(body,groups):
    ob=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m=ob.to_mesh()
    try:
        need(len(m.vertices)==len(body.data.vertices),"NATIVE_SKIN_VERTEX_DOMAIN_DRIFT")
        out={}
        for side in ("L","R"):
            out[side]={}
            for region in ("heel","ball"):
                ids=groups[side][region+"_region_fixed_vertex_ids"]
                pts=[ob.matrix_world@m.vertices[i].co for i in ids]
                need(all(all(math.isfinite(float(z)) for z in p) for p in pts),
                     "NONFINITE_REAL_SKIN_VERTICES")
                out[side][region]={"xy":(sum(float(p.x) for p in pts)/len(pts),
                                         sum(float(p.y) for p in pts)/len(pts)),
                                   "minz":min(float(p.z) for p in pts)}
        return out
    finally:ob.to_mesh_clear()
def metrics(trace):
    n=len(trace)
    need(n==360,"MISSING_ACTUAL_360_60HZ")
    z=[v["minz"] for v in trace];low=min(z)
    speed=[60*math.dist(trace[i]["xy"],trace[i-1]["xy"]) for i in range(1,n)]
    near=[speed[i-1] for i in range(1,n) if z[i]<low+.012 and z[i-1]<low+.012]
    return {"samples_60hz":n,"native_body_region_not_worn_shoe":True,
            "foot_material_fixed_ids":True,
            "global_min_z_m":round(low,6),"global_max_z_m":round(max(z),6),
            "fullclip_p50_xy_speed_mps":round(statistics.median(speed),6),
            "near_own_low_adjacent_pairs":len(near),
            "near_own_low_p50_xy_speed_mps":round(statistics.median(near),6) if near else None,
            "actual_force_support_ground_verified":False}
def viewpoint(camera,target,where,name):
    camera.name="BH_"+name
    camera.location=where
    camera.rotation_euler=(target-camera.location).to_track_quat("-Z","Y").to_euler()
def render_images(body,actor,rig_name,root_before,save_dir,trace,source,source_nodes,mapping,arm,baseline,scale,conv,root0):
    scene=bpy.context.scene
    scene.render.engine="BLENDER_WORKBENCH"
    scene.render.resolution_x=320
    scene.render.resolution_y=320
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.film_transparent=False
    camdata=bpy.data.cameras.new("BH_Camera")
    cam=bpy.data.objects.new("BH_OriginalSyntheticCamera",camdata)
    bpy.context.collection.objects.link(cam)
    camdata.type="ORTHO";camdata.ortho_scale=4.6
    scene.camera=cam
    outfile=[]
    selected=(0,180,359)
    # Fixed view orientation/scale but translate cameras WITH the actual source
    # character; first GHA RED showed static profile camera LOST subject by 3s.
    # Tracking avoids misleading blank-but-distinct image SHA successes.
    for view,eye in (("front",Vector((0,-6,1.1))),("profile",Vector((6,0,1.1)))):
        for idx in selected:
            pose(source["frames"][120+idx],arm,source_nodes,mapping,
                 baseline,scale,conv,root0)
            scene.frame_set(idx)
            bpy.context.view_layer.update()
            subject=arm.matrix_world.translation.copy()
            viewpoint(cam,subject+Vector((0,0,.6)),subject+eye,view)
            bpy.context.view_layer.update()
            filename=f"{actor}_{rig_name}_{view}_{idx:03d}.png"
            out=save_dir/filename
            scene.render.filepath=str(out.resolve())
            bpy.ops.render.render(write_still=True)
            need(out.is_file() and out.stat().st_size>2000,"NO_REAL_BLENDER_RASTER")
            # Independent pixel occupancy metric rejects an empty camera/black
            # off-screen subject, which plain PNG hash changes did not catch.
            im=bpy.data.images.load(str(out.resolve()),check_existing=False)
            try:
                raw=list(im.pixels[:])
                count=sum(1 for k in range(0,len(raw),4)
                          if max(raw[k],raw[k+1],raw[k+2])>.12)
                min_visible=300
                need(count>=min_visible,"NO_VISIBLE_ACTUAL_CHARACTER_PIXELS")
                fraction=round(count/(im.size[0]*im.size[1]),6)
            finally:
                bpy.data.images.remove(im)
            outfile.append({"view":view,"source_index_60hz":idx,
                            "relative_seconds":round(idx/60,6),
                            "png":filename,"png_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
                            "bytes":out.stat().st_size,
                            "visible_nonblack_character_pixels":count,
                            "visible_nonblack_character_fraction":fraction,
                            "camera_follows_original_actor_root":True,
                            "camera_target_m":[round(float(z),6) for z in subject+Vector((0,0,.6))],
                            "body_source_only_CC0_not_photo":True})
    need(len(set(x["png_sha256"] for x in outfile))>=4,
         "VISUALS_NOT_TIME_VARIANT_OR_TWO_VIEWS")
    return outfile
def pose(frame,arm,nodes,mapping,baseline,scale,conv,root0):
    for k,t in mapping.items():
        src=conv@bd.source_rotation(nodes[k],frame)@conv.inverted()
        rb=arm.data.bones[t]
        B=rb.matrix_local.to_3x3()
        if rb.parent:B=rb.parent.matrix_local.to_3x3().inverted()@B
        rot=B.inverted()@src@B
        arm.pose.bones[t].rotation_quaternion=rot.to_quaternion()
    shift=(conv@(bd.source_pos(nodes["Hips"],frame)-root0))*(.01*scale)
    arm.matrix_world=Matrix.Translation(shift)@baseline
    bpy.context.view_layer.update()
def main():
    parser=argparse.ArgumentParser()
    for k in ("actor","rig","motion","out","images"):parser.add_argument("--"+k,required=True)
    a=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    need(a.actor in ("AsterOriginal","JuniperOriginal") and a.rig in ("default","game_engine"),
         "UNAUTHORIZED_SOURCE_AVATAR")
    blob=Path(a.motion).read_bytes()
    need(git_blob_sha(blob)==SOURCE_BLOB,"SOURCE_100STYLE_BLOB_DRIFT")
    source=parse_bvh(blob)
    need(source["count"]==2400 and abs(source["frame_time"]-1/60)<1e-5,
         "SOURCE_60HZ_CLOCK_CHANGED")
    nodes=bd.get_source(source)
    profile=next(p for p in contract.PROFILES if p["name"]==a.actor)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    hs,ts,props=be.setup()
    body,arm,raw,shape,macros,ignored,after,drift=be.create(hs,ts,props,profile,a.rig)
    need(shape["sha256"]!=raw,"RAW_BASE_FINGERPRINT_FALSIFIES_MORPHOLOGY")
    mapping=be.RIGS[a.rig]
    # Research-only unmasked numerical body: fixed material vertex IDs retain
    # source skinning but do NOT represent correct clothes or worn footwear.
    for m in body.modifiers:
        if m.type!="ARMATURE":m.show_viewport=False
    arm.data.pose_position="POSE"
    bpy.context.view_layer.update()
    groups=original_material_ids(body,arm,mapping)
    samples={s:{region:[] for region in ("heel","ball")} for s in ("L","R")}
    conv=Matrix.Rotation(math.pi/2,3,"X")
    sourceleg=(Vector(nodes["LeftKnee"]["offset"]).length+
               Vector(nodes["LeftAnkle"]["offset"]).length)*.01
    joints=be.landmarks(arm,mapping)
    targetleg=(Vector(joints["LeftHip"])-Vector(joints["LeftKnee"])).length+ \
              (Vector(joints["LeftKnee"])-Vector(joints["LeftAnkle"])).length
    need(.4<targetleg<1.4 and .3<sourceleg<1.5,"LEG_SCALE_IMPLAUSIBLE")
    scale=targetleg/sourceleg
    base=arm.matrix_world.copy()
    root0=bd.source_pos(nodes["Hips"],source["frames"][120])
    for bone in arm.pose.bones:
        bone.rotation_mode="QUATERNION"
        bone.rotation_quaternion=Quaternion((1,0,0,0))
        bone.location=(0,0,0)
    for frameidx in range(360):
        pose(source["frames"][120+frameidx],arm,nodes,mapping,base,scale,conv,root0)
        values=observe(body,groups)
        for side in ("L","R"):
            for region in ("heel","ball"):samples[side][region].append(values[side][region])
    results={}
    for side in ("L","R"):
        heel=samples[side]["heel"];ball=samples[side]["ball"]
        relative=[ball[i]["minz"]-heel[i]["minz"] for i in range(360)]
        results[side]={"heel_region":metrics(heel),"ball_region":metrics(ball),
                       "ball_minus_heel_height_p50_m":round(statistics.median(relative),6),
                       "ball_minus_heel_height_min_m":round(min(relative),6),
                       "ball_minus_heel_height_max_m":round(max(relative),6),
                       "true_heel_ball_anatomical_joints_corroborated":False}
    # One body, material, and two independent raster camera views.
    save=Path(a.images);save.mkdir(exist_ok=False,parents=True)
    original=render_images(body,a.actor,a.rig,base,save,samples,
                           source,nodes,mapping,arm,base,scale,conv,root0)
    out={"schema":"scp.n03d-bh.original-mpfb-multi-view-contact-proxy.v1",
         "actor":a.actor,"rig":a.rig,
         "public_original_substitute_only":True,
         "mpfb_official_source_commit":contract.UPSTREAM,
         "motion_git_blob":SOURCE_BLOB,
         "body_actual_evaluated_shape_sha256":shape["sha256"],
         "source_60hz_frames":[120,479],
         "real_blender_5_2_4_version":list(bpy.app.version),
         "fixed_heel_ball_body_vertex_region_receipts":{s:{
           "n_heel":len(groups[s]["heel_region_fixed_vertex_ids"]),
           "n_ball":len(groups[s]["ball_region_fixed_vertex_ids"]),
           "source_weighted_total":groups[s]["selected_source_weighted_vertices"],
           "rest_axis":groups[s]["rest_toe_axis"]} for s in ("L","R")},
         "material_results":results,
         "genuine_blender_workbench_original_source_stills":original,
         "reference_cameras_are_static_per_view":False,
         "reference_camera_angles_fixed_but_track_root":True,
         "all_images_contain_subject_foreground":True,
         "characters_wear_real_CC0_shoes":False,
         "true_anatomical_heel_ball_semantics_calibrated":False,
         "real_force_grf":False,"floor_contact_verified":False,
         "independent_critics_approved_realism":False,
         "protected_actors_or_likeness_used":False,
         "mvp_accepted":False,"status":"PASS_NARROW_NATIVE_HEEL_BALL_PROXY_AND_REAL_RASTER_HOLD_REALISM"}
    Path(a.out).write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("N03D_BH_NATIVE_SKIN_HEEL_BALL_AND_REAL_STILLS",
          json.dumps({k:v for k,v in out.items() if k not in
                      ("genuine_blender_workbench_original_source_stills","material_results")},sort_keys=True),
          flush=True)
if __name__=="__main__":main()
