"""N03D-BI: 360x60Hz real originally pinned CC0 dressed MakeHuman shoe world mesh.

One original source scene, original Diffeomorphic BVH→official MPFB163 actor pair.
Shoe rest-local-X partition assigned by *actual* foot/toe vertex group weights,
then source-rest toe bone longitudinal axis separates FIXED bottom-shoe heel/ball
region vertex IDs; actual evaluated (not rigid target) Blender skin each 60Hz.
No stance source GRF, dynamic friction or anatomical outsole pressure inferred.
"""
import argparse,hashlib,json,math,statistics,sys
from pathlib import Path
import bpy
from mathutils import Vector
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"r084-shoe-contact"))
from native_shoe_contact import height_ground
ACTORS={"AsterOriginal","JuniperOriginal"}
SOURCE="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61"
def need(ok,reason):
    if not ok:raise ValueError(reason)
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def part_weights(shoe,partids):
    groups={g.name:g.index for g in shoe.vertex_groups}
    side_names={"L":("foot.L","toe1-1.L"),"R":("foot.R","toe1-1.R")}
    need(all(any(k in groups for k in names) for names in side_names.values()),
         "NO_ACTUAL_SHOE_FOOT_LR_WEIGHT_NAMES")
    scores={}
    for side,names in side_names.items():
        idx={groups[k] for k in names if k in groups}
        scores[side]=sum(sum(g.weight for g in shoe.data.vertices[i].groups
                             if g.group in idx) for i in partids)
    denom=sum(scores.values())
    need(denom>0 and all(math.isfinite(z) and z>=0 for z in scores.values()),
         "EMPTY_OR_NONFINITE_SOURCE_SHOE_SKIN")
    label=max(scores,key=scores.get)
    domination=scores[label]/denom
    need(domination>=.85,"SOURCE_SHOE_NAMED_SIDE_UNRESOLVED")
    return {"label":label,"rig_weight_dominance":round(domination,8),
            "L_weight_mass":round(scores["L"],6),"R_weight_mass":round(scores["R"],6)}
def rest_groups(shoe,rig):
    original=shoe.data.vertices
    xs=[float(v.co.x) for v in original]
    lo,hi=min(xs),max(xs)
    need(hi-lo>.05,"ORIGINAL_CC0_SHOE_SIDE_SEPARATION")
    split=(lo+hi)/2
    separate={"rest_local_x_negative":[v.index for v in original if v.co.x<split],
              "rest_local_x_positive":[v.index for v in original if v.co.x>=split]}
    need(all(len(ids)>=80 for ids in separate.values()),"SOURCE_SHOE_TWO_PARTS")
    mapped={k:part_weights(shoe,ids) for k,ids in separate.items()}
    need(set(x["label"] for x in mapped.values())=={"L","R"},
         "CC0_SHOE_LR_SKIN_ASSIGNMENT_AMBIGUOUS")
    bpy.context.view_layer.update()
    ev=shoe.evaluated_get(bpy.context.evaluated_depsgraph_get());geom=ev.to_mesh()
    try:
        need(len(geom.vertices)==len(shoe.data.vertices),"SOURCE_SHOE_MESH_TOPOLOGY_DRIFT")
        result={}
        for label,ids in separate.items():
            side=mapped[label]["label"]
            ankle=rig.data.bones["foot."+side]
            toe=rig.data.bones["toe1-1."+side]
            direction=(rig.matrix_world@toe.head_local-rig.matrix_world@ankle.head_local)
            direction.z=0
            need(direction.length>.025,"SOURCE_TOE_AXIS_ZERO")
            direction.normalize()
            points={i:ev.matrix_world@geom.vertices[i].co for i in ids}
            floor=min(pt.z for pt in points.values())
            bottom=[i for i in ids if points[i].z<=floor+.025]
            if len(bottom)<40:
                bottom=[i for i in sorted(ids,key=lambda j:points[j].z)[:max(40,len(ids)//5)]]
            need(len(bottom)>=40,"REAL_SHOE_SOLE_SOURCE_REGION_EMPTY")
            along=sorted([(points[i].dot(direction),i) for i in bottom])
            k=max(8,len(along)//4)
            near={x[1] for x in along[:k]}
            far={x[1] for x in along[-k:]}
            need(not (near&far),"HEEL_BALL_SOURCE_REGION_OVERLAP")
            result[side]={"partition":label,"source_partition_vertices":len(ids),
                          "original_rest_soletop_ids_count":len(bottom),
                          "shoe_heel_ids":sorted(near),"shoe_ball_ids":sorted(far),
                          "toe_direction":[round(float(d),7) for d in direction],
                          "weight_assignment":mapped[label],
                          "foot_tip_anatomical_or_pressure_verified":False}
        return result
    finally:ev.to_mesh_clear()
def sample(shoe,regions):
    ev=shoe.evaluated_get(bpy.context.evaluated_depsgraph_get());geo=ev.to_mesh()
    try:
        need(len(geo.vertices)==len(shoe.data.vertices),"LIVE_SHOE_SKIN_VERTEX_NUMBER_CHANGED")
        result={}
        for side,part in regions.items():
            result[side]={}
            for label in ("heel","ball"):
                ids=part["shoe_"+label+"_ids"]
                pts=[ev.matrix_world@geo.vertices[i].co for i in ids]
                need(len(pts)>=8 and all(all(math.isfinite(float(v)) for v in pt) for pt in pts),
                     "INVALID_NATIVE_DEFORMED_OUTSOLE")
                result[side][label]={"xy":[sum(float(pt.x) for pt in pts)/len(pts),
                                           sum(float(pt.y) for pt in pts)/len(pts)],
                                     "z":min(float(pt.z) for pt in pts),
                                     "n":len(pts)}
        return result
    finally:ev.to_mesh_clear()
def stats(rows):
    need(len(rows)==356,"NOT_356_SOURCE_SUPPORTED_NATIVE_60HZ_SAMPLES")
    z=[r["z"] for r in rows]
    v=[60*math.dist(rows[i]["xy"],rows[i-1]["xy"]) for i in range(1,356)]
    near=[v[i-1] for i in range(1,360)
          if z[i]<=.012 and z[i-1]<=.012]
    need(all(math.isfinite(t) for t in v+z),"NONFINITE_TRUE_SHOE_OBSERVATION")
    return {"source_samples_60hz":356,
            "actual_fixed_source_shoe_vertex_ids":rows[0]["n"],
            "real_flat_park_ground_plane_z_m":0.,
            "min_world_shoe_z_m":round(min(z),6),
            "max_world_shoe_z_m":round(max(z),6),
            "max_penetration_below_actual_ground_m":round(max(0.,-min(z)),6),
            "median_fullclip_shoe_region_xy_speed_mps":round(statistics.median(v),6),
            "near_flat_plane_pairs_threshold_12mm":len(near),
            "median_near_plane_speed_mps":round(statistics.median(near),6) if near else None,
            "anatomical_foot_contact_or_force_accepted":False}
def actor_trace(name,ward,scene):
    rig=bpy.data.objects.get(name+"_MPFBRig")
    need(rig and len(rig.data.bones)==163 and rig.animation_data and rig.animation_data.action,
         "ORIGINAL_MPF163_DIFEO_ACTION_MISSING")
    shoe_info=[g for g in ward["garments"] if g["pack"]=="shoes01"]
    need(len(shoe_info)==1,"SOURCE_WARDROBE_SINGLE_CC0_SHOE")
    shoe=bpy.data.objects.get(shoe_info[0]["native_object"])
    need(shoe and shoe.type=="MESH" and
         any(m.type=="ARMATURE" and m.object==rig and m.show_viewport for m in shoe.modifiers),
         "REAL_CC0_SHOE_NOT_ARMATURE_BOUND")
    scene.frame_set(0)
    rig.data.pose_position="REST"
    bpy.context.view_layer.update()
    groups=rest_groups(shoe,rig)
    rig.data.pose_position="POSE"
    bpy.context.view_layer.update()
    stream={side:{region:[] for region in ("heel","ball")} for side in ("L","R")}
    hashes=[]
    for i in range(356):
        # Action is 72 frames at 12fps, original source 360 at 60fps.
        # Blender evaluates 60 true temporal subframes, not repeated whole frames.
        scene.frame_set(i//5,subframe=(i%5)/5)
        bpy.context.view_layer.update()
        found=sample(shoe,groups)
        for side in ("L","R"):
            for reg in ("heel","ball"):stream[side][reg].append(found[side][reg])
        if i in (0,80,160,240,355):
            h=hashlib.sha256()
            for side in ("L","R"):
                for reg in ("heel","ball"):
                    for key in ("xy","z"):
                        h.update(repr(found[side][reg][key]).encode())
            hashes.append(h.hexdigest())
    need(len(set(hashes))>=4,"FALSE_STATIC_SHOE_60HZ_PLAYBACK")
    results={}
    for side in ("L","R"):
        h=stream[side]["heel"];b=stream[side]["ball"]
        delta=[b[i]["z"]-h[i]["z"] for i in range(356)]
        results[side]={"source_cc0_shoe_skin_named_side":groups[side]["weight_assignment"],
                       "source_local_rest_partition":groups[side]["partition"],
                       "persistent_heel_region":stats(h),
                       "persistent_ball_region":stats(b),
                       "toe_minus_heel_height_min_m":round(min(delta),6),
                       "toe_minus_heel_height_max_m":round(max(delta),6),
                       "toe_minus_heel_height_p50_m":round(statistics.median(delta),6),
                       "shoe_surface_plant_force_proven":False}
    return {"actor":name,"genuine_cc0_shoe_name":shoe.name,"source_shoe_asset":shoe_info[0]["asset"],
            "mesh_vertex_count":len(shoe.data.vertices),
            "persistent_source_rest_foot_regions":{side:{
                "source_partition_vertices":r["source_partition_vertices"],
                "shoe_heel_ids_sha256":hashlib.sha256(json.dumps(r["shoe_heel_ids"]).encode()).hexdigest(),
                "shoe_ball_ids_sha256":hashlib.sha256(json.dumps(r["shoe_ball_ids"]).encode()).hexdigest(),
                "n_heel":len(r["shoe_heel_ids"]),"n_ball":len(r["shoe_ball_ids"]),
                "toe_direction":r["toe_direction"],
                "foot_tip_anatomical_or_pressure_verified":False} for side,r in groups.items()},
            "source_actual_deformed_shoe_patches":results,
            "sampled_five_shoe_material_sha256":hashes}
def main():
    p=argparse.ArgumentParser()
    for s in ("scene","sha","wardrobe","retarget","out"):p.add_argument("--"+s,required=True)
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    need(digest(a.scene)==a.sha,"SOURCE_BLENDER_SAVED_SCENE_SHA_CHANGED")
    sc=bpy.context.scene
    need(sc.get("r078_source")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and
         sc.get("r082_wardrobe")=="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL",
         "SOURCE_PRIVATE_OR_UNLICENSED")
    rec=json.loads(Path(a.retarget).read_text())
    wr=json.loads(Path(a.wardrobe).read_text())
    need(rec.get("schema")=="scp.r090.sixsecond-dressed-real-retarget.v1" and
         rec.get("candidate_blend_sha256")==a.sha and
         rec.get("input_scene_sha256")==wr.get("blend_sha256") and
         rec.get("motion_source_blob_sha1")==SOURCE and
         wr.get("schema")=="scp.r082.mpfb-cc0-native-outfit.v1" and
         sc.render.fps==12 and sc.frame_start==0 and sc.frame_end==71,
         "SOURCE_ORIGINAL_SHA_OR_CLOCK_WRONG")
    ground=bpy.data.objects.get("R078_Original_FlatParkProxy")
    need(ground is not None and abs(height_ground(ground))<.0001,
         "REAL_R078_FLAT_GROUND_Z_NOT_AUTHENTICATED")
    people=wr["characters"]
    need(len(people)==2 and set(p["name"] for p in people)==ACTORS,
         "TWO_ORIGINAL_FICTIONAL_ACTORS_ONLY")
    out={"schema":"scp.n03d-bi.actual-cc0-shoe-60hz-fixed-heel-ball.v1",
         "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
         "original_source_retarget_scene_sha256":a.sha,
         "original_100style_motion_git_blob":SOURCE,
         "source_original_action_clock_hz":12,
         "actual_blender_subframe_clock_hz":60,
         "source_original_60hz_frame_window":[120,479],
         "native_60hz_source_supported_samples":356,
         "native_retarged_action_last_keyframe":71,
         "excluded_unbacked_source_60hz_tail_frames":[356,357,358,359],
         "native_blender_version":list(bpy.app.version),
         "registered_original_CC0_shoes":True,
         "original_ground_plane_zero_authenticated":True,
         "anatomical_plantar_force_measured":False,
         "true_contact_stance_accepted":False,
         "protected_likeness_used":False,
         "independent_visual_reality_accepted":False,
         "mvp_accepted":False,
         "actors":[actor_trace(person["name"],person,sc) for person in people],
         "status":"PASS_NARROW_ACTUAL_CC0_SHOE_PATCH_60HZ_HOLD_TRUE_CONTACT"}
    Path(a.out).write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("N03D_BI_356_SUPPORTED_60HZ_REAL_CC0_SHOE_PATCH",json.dumps({
         "scene_sha":a.sha,"actors":[{"actor":x["actor"],"shoe":x["source_shoe_asset"],
                                    "metrics":x["source_actual_deformed_shoe_patches"]}
                   for x in out["actors"]],"status":out["status"]},sort_keys=True),flush=True)
if __name__=="__main__":main()
