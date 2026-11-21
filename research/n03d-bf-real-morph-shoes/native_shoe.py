"""N03D-BF: same-source same-phenotype MPFB default163/game_engine53 real CC0 shoe dynamics.

Actual source-authenticated shoe garments are fitted to BOTH official skeletons
of EACH identical original Aster/Juniper phenotype, and evaluated on the SAME
100STYLE 360x60Hz source for direct vs rest-conjugated mappings. Material IDs
are fixed from the rest pose, heel/toe PROXIES derived from rig toe direction
not externally authenticated landmarks. All physical and visual MVP HOLD.
"""
import argparse,hashlib,json,math,statistics,sys,zipfile
from pathlib import Path
import bpy
from mathutils import Matrix,Vector,Quaternion

HERE=Path(__file__).parent
sys.path.insert(0,str(HERE.parent/"n03d-be-same-morph"))
import native as be
sys.path.insert(0,str(HERE.parent/"r082-mpfb-native-wardrobe"))
import wardrobe_contract as wardrobe
sys.path.insert(0,str(HERE.parent/"r088-motion-real"))
from bvh_preflight import parse_bvh,git_blob_sha
from native import source_rotation,source_pos

SOURCE_BLOB="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61"
SHOE_SHA=wardrobe.PACKS["shoes01"]["sha256"]
ANATOMY={"default":{"L":"toe1-1.L","R":"toe1-1.R"},
         "game_engine":{"L":"ball_l","R":"ball_r"}}
def need(x,code):
    if not x:raise ValueError(code)
def finite(x):
    need(math.isfinite(x) and abs(x)<1e3,"NONFINITE_NATIVE_GEOMETRY")
    return float(x)
def shoe_asset(z,actors,workdir,hs):
    found={}
    for a in actors:
        identity=a["actor"]
        shoe_name=next(item[1] for item in wardrobe.OUTFITS[identity] if item[0]=="shoes01")
        relative,members=wardrobe.select_bytes(z,shoe_name)
        for member in members:z.extract(member,path=workdir)
        filepath=Path(workdir)/relative
        need(filepath.is_file(),"SOURCE_CC0_SELECTED_SHOE_UNAVAILABLE")
        for rig_name,item in a["versions"].items():
            body=item["body"];rig=item["rig"]
            bpy.ops.object.select_all(action="DESELECT")
            body.select_set(True);bpy.context.view_layer.objects.active=body
            g=hs.add_mhclo_asset(str(filepath.resolve()),body,asset_type="Clothes",
                                 subdiv_levels=0,material_type="NONE",
                                 set_up_rigging=True,interpolate_weights=True,
                                 import_subrig=True,import_weights=True)
            need(g and g.type=="MESH" and len(g.data.vertices)>=200,"MISSING_NATIVE_REAL_SHOE_MESH")
            need(any(x.type=="ARMATURE" and x.object==rig for x in g.modifiers),
                 "ACTUAL_SHOE_NOT_SKINNED_TO_MATCHED_RIG")
            g.name=f"{identity}_{rig_name}_CC0_{shoe_name}"
            item["shoe"]=g
            item["shoe_source_asset"]=shoe_name
            found[f"{identity}:{rig_name}"]={"garment":shoe_name,
                                              "shoe_total_vertices":len(g.data.vertices),
                                              "armature":rig.name,"actual_skin":True}
    return found
def capture(shoe,ids):
    ev=shoe.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=ev.to_mesh()
    try:
        need(len(mesh.vertices)==len(shoe.data.vertices),"SHOE_TOPOLOGY_CHANGED")
        pts=[ev.matrix_world@mesh.vertices[i].co for i in ids]
    finally:ev.to_mesh_clear()
    need(len(pts)>=5,"SHOE_MATERIAL_COHORT_EMPTY")
    return {"x":finite(sum(p.x for p in pts)/len(pts)),
            "y":finite(sum(p.y for p in pts)/len(pts)),
            "z":finite(min(p.z for p in pts))}
def shoe_groups(shoe,rig,mapping,rig_name):
    """Foot-weight assigned sides, rest low 20%, toe-axis further 30% extrema.

    Real mesh with fixed material vertex IDs; not proof of plantar anatomy.
    """
    bpy.context.view_layer.update()
    out={};audit={}
    for side in ("L","R"):
        key=mapping["LeftAnkle" if side=="L" else "RightAnkle"]
        group=shoe.vertex_groups.get(key)
        need(group is not None,"SHOE_MISSING_WEIGHTED_FOOT_"+key)
        candidates=[v.index for v in shoe.data.vertices
                    if sum(w.weight for w in v.groups if w.group==group.index)>=.35]
        need(len(candidates)>=24,"INSUFFICIENT_SIDE_WEIGHTED_SHOE")
        er=shoe.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh=er.to_mesh()
        try:
            points={i:er.matrix_world@mesh.vertices[i].co for i in candidates}
        finally:er.to_mesh_clear()
        # Stable low foot-vertex cohort; side skin weights overrule world-X split.
        ids=sorted(candidates,key=lambda i:points[i].z)[:max(12,int(.20*len(candidates)))]
        need(len(ids)>=12,"LOW_SHOE_COHORT_INSUFFICIENT")
        foot=rig.data.bones[key]
        toe_key=ANATOMY[rig_name][side]
        need(toe_key in rig.data.bones,"REST_TOE_AXIS_MISSING_"+toe_key)
        toe=rig.data.bones[toe_key]
        # Source canonical toe-head to foot-head is a proxy only, no force/sole verification.
        axis=Vector(toe.head_local-foot.head_local)
        axis.z=0
        need(axis.length>.01,"REST_TOE_AXIS_DEGENERATE")
        axis.normalize()
        scored=sorted(((points[i].dot(axis),i) for i in ids))
        n=max(5,len(scored)//3)
        parts={"heel_proxy":[i for _,i in scored[:n]],
               "toe_proxy":[i for _,i in scored[-n:]],
               "full_low_cohort":ids}
        out[side]=parts
        audit[side]={"source_foot_group":key,"toe_axis_bone":toe_key,
                     "weighted_shoe_vertices":len(candidates),
                     "persistent_low_vertices":len(ids),
                     "heel_proxy_vertices":len(parts["heel_proxy"]),
                     "toe_proxy_vertices":len(parts["toe_proxy"]),
                     "actual_anatomical_sole_heel_toe_verified":False,
                     "side_assigned_from_real_source_skin_weights":True}
    return out,audit
def summarise(series):
    n=len(series)
    need(n==360,"MISSING_SOURCE_RATE")
    z=[r["z"] for r in series]
    speed=[math.hypot(series[i]["x"]-series[i-1]["x"],series[i]["y"]-series[i-1]["y"])*60
           for i in range(1,n)]
    near=[speed[i-1] for i in range(1,n) if z[i]<=min(z)+.012 and z[i-1]<=min(z)+.012]
    return {"samples_60hz":n,"min_native_mesh_z_m":round(min(z),6),
            "max_native_mesh_z_m":round(max(z),6),
            "max_reference_penetration_known":False,
            "fullclip_p50_persistent_material_xy_speed_mps":round(statistics.median(speed),6),
            "fullclip_max_persistent_material_xy_speed_mps":round(max(speed),6),
            "low_relative_adjacent_pairs":len(near),
            "low_relative_p50_persistent_material_xy_speed_mps":round(statistics.median(near),6) if near else None,
            "sole_labeled_anatomically":False,"physical_contact_accepted":False}
def simulate(actor,bvh,nodes):
    out=[]
    basis=Matrix.Rotation(math.pi/2,3,"X")
    root0=source_pos(nodes["Hips"],bvh["frames"][120])
    source_length=(Vector(nodes["LeftKnee"]["offset"]).length+
                   Vector(nodes["LeftAnkle"]["offset"]).length)*.01
    for rig_name,item in actor["versions"].items():
        rig=item["rig"];shoe=item["shoe"];mapping=be.MAP[rig_name]
        need(all(b in rig.pose.bones for b in mapping.values()),"TARGET_LOWER_BONE_MISSING")
        cache,cache_audit=shoe_groups(shoe,rig,mapping,rig_name)
        orig_matrix=rig.matrix_world.copy()
        target_length=rig.data.bones[mapping["LeftHip"]].length+rig.data.bones[mapping["LeftKnee"]].length
        ratio=target_length/source_length
        need(.2<ratio<2,"RIG_SCALE_BAD")
        for mode in be.MODES:
            for pb in rig.pose.bones:
                pb.rotation_mode="QUATERNION";pb.rotation_quaternion=Quaternion((1,0,0,0))
                pb.location=(0,0,0)
            bpy.context.view_layer.update()
            tracks={side:{region:[] for region in ("heel_proxy","toe_proxy","full_low_cohort")} for side in ("L","R")}
            for frame_index in range(360):
                frame=bvh["frames"][120+frame_index]
                for src,target in mapping.items():
                    q=basis@source_rotation(nodes[src],frame)@basis.inverted()
                    pb=rig.pose.bones[target]
                    if mode=="rest_frame_conjugated":
                        rest=pb.bone.matrix_local.to_3x3()
                        if pb.bone.parent:
                            rest=pb.bone.parent.matrix_local.to_3x3().inverted()@rest
                        q=rest.inverted()@q@rest
                    pb.rotation_quaternion=q.to_quaternion()
                root=basis@(source_pos(nodes["Hips"],frame)-root0)
                rig.matrix_world=Matrix.Translation(root*.01*ratio)@orig_matrix
                bpy.context.view_layer.update()
                for side,regions in cache.items():
                    for region,idxs in regions.items():
                        tracks[side][region].append(capture(shoe,idxs))
            out.append({"actor":actor["actor"],"rig":rig_name,"mode":mode,
                        "source_frames":[120,479],"native_source_fps":60,
                        "source_body_shape_max_delta_m":actor["shape"]["max_rest_vertex_deviation_m"],
                        "rig_bones":item["count"],"actual_mesh_source_asset":item["shoe_source_asset"],
                        "actual_original_CC0_shoe_skinned":True,
                        "original_rig_rest_toe_proxy":cache_audit,
                        "native_60hz_shoe_material":{
                            side:{region:summarise(seq) for region,seq in parts.items()}
                            for side,parts in tracks.items()},
                        "ground_contact_true":False,"anatomical_sole_verified":False,
                        "visual_accepted":False,"physical_gait_accepted":False})
        rig.matrix_world=orig_matrix
    return out
def main():
    a=argparse.ArgumentParser()
    for key in ("source","motion","shoe-archive","work","out"):a.add_argument("--"+key,required=True)
    args=a.parse_args(sys.argv[sys.argv.index("--")+1:])
    need(Path(args.source,"src/mpfb/data/3dobjs/base.obj").is_file(),"NOT_OFFICIAL_MPF_SOURCE")
    blob=Path(args.motion).read_bytes()
    need(Path(args.motion).name=="Neutral_FW.bvh" and git_blob_sha(blob)==SOURCE_BLOB,"SOURCE_GAIT_GIT_BLOB")
    bvh=parse_bvh(blob)
    need(bvh["count"]==2400 and abs(bvh["frame_time"]-1/60)<1e-5,"SOURCE_RATE")
    sha=hashlib.sha256(Path(args.shoe_archive).read_bytes()).hexdigest()
    need(sha==SHOE_SHA,"SHOE_CC0_SOURCE_SHA_PIN")
    zip_=wardrobe.source_archive("shoes01",Path(args.shoe_archive).read_bytes())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    hs,ts,props=be.services()
    actors=be.build_pair(hs,ts,props)
    need(len(actors)==2 and all(set(a["versions"])==set(be.RIGS) for a in actors),"TRUE_BODY_RIG_PAIRS")
    shoes=shoe_asset(zip_,actors,args.work,hs)
    nodes={n["name"]:n for n in bvh["nodes"] if not n["end"]}
    trials=[]
    for actor in actors:trials.extend(simulate(actor,bvh,nodes))
    shape=[{"name":a["actor"],"default_bones":a["versions"]["default"]["count"],
            "game_engine_bones":a["versions"]["game_engine"]["count"],
            "body_rest_vertex_delta":a["shape"]} for a in actors]
    report={"schema":"scp.n03d-bf.identical-morphology-real-cc0-worn-footwear.v1",
            "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
            "MPFB_upstream_commit":be.c.UPSTREAM,
            "source_original_100style_blob":SOURCE_BLOB,
            "source_original_100style_sha256":hashlib.sha256(blob).hexdigest(),
            "original_cc0_shoe_pack_sha256":SHOE_SHA,
            "official_Blender_version":list(bpy.app.version),
            "source_original_rate_hz":60,"source_frames":[120,479],
            "true_skin_model_actors":shape,
            "actual_shoe_sources":shoes,
            "source_body_cloth_or_shoe_saved":False,
            "raw_100style_media_published":False,
            "true_contact_force_measured":False,"true_anatomical_heel_toe_verified":False,
            "source_floor_measured":False,"independent_visual_accepted":False,
            "physical_gait_accepted":False,"mvp_accepted":False,
            "status":"HOLD_PHYSICAL_CONTACT_AND_VISUAL",
            "actual_native_360x60hz_trials":trials}
    need(len(trials)==8,"MISSING_CROSS_RIG_REAL_SKIN_DOE")
    Path(args.out).write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("N03D_BF_REAL_CC0_MATCHED_MORPH_NATIVE_MATERIAL",
          json.dumps({"shape":shape,"shoes":shoes,
                      "trials":[{"actor":v["actor"],"rig":v["rig"],"mode":v["mode"],
                                 "measure":v["native_60hz_shoe_material"]} for v in trials],
                      "status":report["status"]},sort_keys=True),flush=True)
if __name__=="__main__":main()
