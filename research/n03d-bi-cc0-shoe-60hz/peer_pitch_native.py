"""Actual CC0 MPFB Blender shoe heel/ball chord-vs-horizontal pitch witness.

Reads a SHA-pinned original fictional CC0 source scene and fixed material cohorts.
Never rotates or edits the rig/shoe, never claims physical contact or correction.
"""
import argparse
import json
import math
import sys
import hashlib
from pathlib import Path
import bpy

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from native import rest_groups, digest, need
from peer_pitch_geometry import measure

SAMPLES=(0,80,160,240,355)


def centroid(positions):
    n=len(positions)
    need(n>=8,"EMPTY_REAL_OUTSOLE_REGION")
    return tuple(sum(float(p[k]) for p in positions)/n for k in range(3))


def mesh_witness(shoe, regions):
    evaluated=shoe.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evaluated.to_mesh()
    try:
        need(len(mesh.vertices)==len(shoe.data.vertices),"SHOE_VERTEX_TOPOLOGY_CHANGED")
        points=[evaluated.matrix_world@v.co for v in mesh.vertices]
        out={}
        for side,region in regions.items():
            h=[points[i] for i in region["shoe_heel_ids"]]
            b=[points[i] for i in region["shoe_ball_ids"]]
            hp=centroid(h);bp=centroid(b)
            d=measure(hp,bp)
            # Independent geometric minimum across full side mesh, not just
            # heel/ball landmark centroids and not a circular corrective lift.
            min_z=min(float(points[i].z) for i in
                      ([*region["shoe_heel_ids"],*region["shoe_ball_ids"]]))
            d["min_source_heel_ball_cohort_world_z_m"]=round(min_z,8)
            d["cohort_ground_penetration_m"]=round(max(0.0,-min_z),8)
            d["heel_count"]=len(h)
            d["ball_count"]=len(b)
            out[side]=d
        return out
    finally:
        evaluated.to_mesh_clear()


def main():
    p=argparse.ArgumentParser()
    for x in ("scene","sha","wardrobe","retarget","out"):
        p.add_argument("--"+x,required=True)
    args=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    need(digest(args.scene)==args.sha,"EXACT_SCENE_SHA")
    sc=bpy.context.scene
    need((sc.frame_start,sc.frame_end,sc.render.fps)==(0,71,12),"LEGACY_NATIVE_SCENE_CLOCK")
    need(sc.get("r078_source")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and
         sc.get("r082_wardrobe")=="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL","PROTECTED_SOURCE_NOT_ADMITTED")
    ward=json.loads(Path(args.wardrobe).read_text())
    ret=json.loads(Path(args.retarget).read_text())
    need(ret.get("candidate_blend_sha256")==args.sha and
         ret.get("input_scene_sha256")==ward.get("blend_sha256") and
         ret.get("motion_source_blob_sha1")=="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61",
         "ORIGINAL_MOTION_SOURCE_JOIN")
    actors=[]
    for entry in ward["characters"]:
        name=entry["name"]
        need(name in ("AsterOriginal","JuniperOriginal"),"ORIGINAL_ACTOR_RIGHTS")
        rig=bpy.data.objects.get(name+"_MPFBRig")
        shoe_entries=[g for g in entry["garments"] if g["pack"]=="shoes01"]
        need(rig and len(shoe_entries)==1,"SOURCE_RIG_OR_SHOE_NOT_FOUND")
        shoe=bpy.data.objects.get(shoe_entries[0]["native_object"])
        need(shoe is not None and any(m.type=="ARMATURE" and m.object==rig for m in shoe.modifiers),
             "CC0_SHOE_NOT_SKINNED")
        sc.frame_set(0)
        rig.data.pose_position="REST"
        bpy.context.view_layer.update()
        regions=rest_groups(shoe,rig)
        rig.data.pose_position="POSE"
        frames=[]
        for i in SAMPLES:
            sc.frame_set(i//5,subframe=(i%5)/5)
            bpy.context.view_layer.update()
            observed=mesh_witness(shoe,regions)
            frames.append({"source_60hz_sample_index":i,
                           "source_sample_time_s":round(i/60.0,9),
                           "left":observed["L"],"right":observed["R"]})
        actors.append({"name":name,"original_cc0_shoe_asset":shoe_entries[0]["asset"],
                       "source_shoe_object":shoe.name,"sampled_original_geometry":frames})
    need({a["name"] for a in actors}=={"AsterOriginal","JuniperOriginal"},"ACTORS_INCOMPLETE")
    result={"schema":"scp.r009.peer-original-shoe-pitch-world-v1",
            "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
            "source_scene_sha256":args.sha,
            "original_motion_git_blob_sha1":"a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61",
            "sampled_60hz_indices":list(SAMPLES),
            "total_original_60hz_source_frames":360,
            "supported_by_legacy_scene":356,
            "physical_contact_accepted":False,
            "protected_likeness_used":False,
            "mvp_accepted":False,"status":"HOLD",
            "actors":actors}
    Path(args.out).write_text(json.dumps(result,sort_keys=True,allow_nan=False)+"\n")
    print("R009_ORIGINAL_CC0_REAL_SHOE_WORLD_PITCH_DIAGNOSTIC",json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
