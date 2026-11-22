"""True-native-360 Blender CC0 shoe full-clip observer; no mutation or contact claim."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from shoe360_metrics import analyze
sys.path.insert(0,str(HERE.parent/"n03d-bi-cc0-shoe-60hz"))
from native import rest_groups, digest


def need(ok,code):
    if not ok:
        raise RuntimeError(code)


def sample_world_mesh(shoe,side_ids,regions,index):
    ev=shoe.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=ev.to_mesh()
    try:
        need(len(mesh.vertices)==len(shoe.data.vertices),"SOURCE_SHOE_VERTEX_ID_DRIFT")
        xyz=[ev.matrix_world@v.co for v in mesh.vertices]
        def centroid_xy(ids):
            need(len(ids)>=8,"SOURCE_FIXED_COHORT_MISSING")
            n=len(ids)
            return [sum(float(xyz[i].x) for i in ids)/n,
                    sum(float(xyz[i].y) for i in ids)/n]
        def min_z(ids):
            result=min(float(xyz[i].z) for i in ids)
            need(math.isfinite(result),"NONFINITE_REAL_SHOE_Z")
            return result
        results={}
        for side,group in regions.items():
            heel=group["shoe_heel_ids"]
            ball=group["shoe_ball_ids"]
            results[side]={
                "frame":index,"t":round(index/60.0,9),
                "heel_xy":centroid_xy(heel),
                "ball_xy":centroid_xy(ball),
                "heel_min_z":min_z(heel),
                "ball_min_z":min_z(ball),
                "world_shoe_side_min_z":min_z(side_ids[side]),
            }
        return results
    finally:
        ev.to_mesh_clear()


def main():
    parser=argparse.ArgumentParser()
    for key in ("scene","sha","wardrobe","clock-report","out"):
        parser.add_argument("--"+key,required=True)
    a=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    need(digest(a.scene)==a.sha,"SOURCE_NATIVE_360_SCENE_SHA")
    report=json.loads(Path(a.clock_report).read_text())
    need(report.get("candidate_blend_sha256")==a.sha and
         report.get("status")=="HOLD_NATIVE_CLOCK_EXPERIMENT" and
         report.get("physical_contact_accepted") is False and
         report.get("mvp_accepted") is False,"UNVERIFIED_SOURCE_CLOCK_OR_FALSE_ADMISSION")
    sc=bpy.context.scene
    need((sc.render.fps,sc.render.fps_base,sc.frame_start,sc.frame_end)==(60,1.0,0,359),
         "NO_NATIVE_360_AT_60_SCENE")
    need(sc.get("r078_source")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and
         sc.get("r082_wardrobe")=="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL",
         "PROTECTED_MEDIA_NOT_ADMITTED")
    ward=json.loads(Path(a.wardrobe).read_text())
    people=ward["characters"]
    need({p["name"] for p in people}=={"AsterOriginal","JuniperOriginal"},
         "ORIGINAL_CC0_ACTORS_MISSING")
    actors=[]
    for p in people:
        name=p["name"]
        rig=bpy.data.objects.get(name+"_MPFBRig")
        shoes=[g for g in p["garments"] if g["pack"]=="shoes01"]
        need(rig and len(shoes)==1,"REAL_ORIGINAL_SHOE_OR_RIG_MISSING")
        shoe=bpy.data.objects.get(shoes[0]["native_object"])
        need(shoe is not None and any(m.type=="ARMATURE" and m.object==rig
                                   for m in shoe.modifiers),"ACTUAL_CC0_SKIN_NOT_BOUND")
        sc.frame_set(0)
        rig.data.pose_position="REST"
        bpy.context.view_layer.update()
        regions=rest_groups(shoe,rig)
        xs=[float(v.co.x) for v in shoe.data.vertices]
        center=(min(xs)+max(xs))/2.0
        partitions={
            "rest_local_x_positive":[i for i,x in enumerate(xs) if x>=center],
            "rest_local_x_negative":[i for i,x in enumerate(xs) if x<center],
        }
        side_ids={side:partitions[region["partition"]] for side,region in regions.items()}
        need(all(len(ids)>100 for ids in side_ids.values()) and
             set(side_ids)=={"L","R"},"ACTUAL_SHOE_LR_REGIONS_INVALID")
        rig.data.pose_position="POSE"
        rows={"L":[],"R":[]}
        for i in range(360):
            sc.frame_set(i)
            bpy.context.view_layer.update()
            measured=sample_world_mesh(shoe,side_ids,regions,i)
            for side in ("L","R"):
                rows[side].append(measured[side])
        actors.append({
            "name":name,
            "source_shoe":shoes[0]["asset"],
            "native_shoe":shoe.name,
            "sides":{side:{"fixed_full_shoe_vertex_ids":len(side_ids[side]),
                           "fixed_heel_vertex_ids":len(regions[side]["shoe_heel_ids"]),
                           "fixed_ball_vertex_ids":len(regions[side]["shoe_ball_ids"]),
                           "metrics":analyze(rows[side]),
                           "rows":rows[side]} for side in ("L","R")},
        })
    need(len(actors)==2,"SAMPLE_TWO_ACTORS_INCOMPLETE")
    output={
        "schema":"scp.r009.peer-original-native360-shoe-fullclip-v1",
        "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
        "exact_native_blend_sha256":a.sha,
        "native_clock_source_sha256":digest(a.clock_report),
        "source_60hz_frame_count":360,
        "original_motion_git_blob_sha1":"a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61",
        "physical_contact_accepted":False,
        "anatomical_outsole_accepted":False,
        "ground_reaction_force_measured":False,
        "protected_likeness_used":False,
        "mvp_accepted":False,
        "status":"HOLD",
        "actors":actors,
    }
    Path(a.out).write_text(json.dumps(output,sort_keys=True,allow_nan=False)+"\n")
    print("R009_TRUE_NATIVE_360_CC0_FULLCLIP_CONTACT_UNKNOWN",
          json.dumps({"scene_sha":a.sha,
             "source":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
             "actors":[{"name":p["name"],
                        "sides":{side:p["sides"][side]["metrics"]
                                 for side in ("L","R")}} for p in actors],
             "status":"HOLD"},sort_keys=True),flush=True)


if __name__=="__main__":
    main()
