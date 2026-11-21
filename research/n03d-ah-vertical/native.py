"""N03D-AH actual vertical floor-proxy interventions on true MPFB skinned shoes.

Reuse AG's source-controlled temporary Blender root and both five-bone IK rigs.
No saved corrected source motion, no true force contact, independent critic HOLD.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector

HERE=Path(__file__).parent
sys.path.insert(0,str(HERE.parent/"n03d-ag-dual-native"))
from native import seek,mesh_world,bone_world,pose,shortest,observe,setup,clear
from plan import actor_plan,ACTORS,SIDES
from material import select_ids
sys.path.insert(0,str(HERE))
from vertical import MODES,BOUNDS,proposal,check_plan,temporal_metrics
from policy import assess

def require(x,code):
    if not x:raise RuntimeError(code)

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    for field in ("scene","sha","wardrobe","retarget","trace","ac","out"):
        parser.add_argument("--"+field,required=True)
    a=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    require(digest(a.scene)==a.sha,"SCENE_SHA_PIN")
    scene=bpy.context.scene
    require(scene.get("r078_source")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and
            scene.get("r082_wardrobe")=="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL",
            "SOURCE_PROTECTED_OR_UNAUTHENTICATED")
    require((scene.frame_start,scene.frame_end,scene.render.fps)==(0,71,12),"SCENE_TIMING")
    wardrobe=json.loads(Path(a.wardrobe).read_text())
    retarget=json.loads(Path(a.retarget).read_text())
    trace=json.loads(Path(a.trace).read_text())
    ac=json.loads(Path(a.ac).read_text())
    require(retarget["candidate_blend_sha256"]==a.sha and
            retarget["input_scene_sha256"]==wardrobe["blend_sha256"] and
            trace["source_scene_sha256"]==a.sha and
            ac["source_scene_sha256"]==a.sha and
            ac["source_shoe_trace_sha256"]==digest(a.trace) and
            ac["schema"]=="scp.n03d-ac.matched-source-to-bone-60hz.v1",
            "SOURCE_SHA_JOIN")
    require(len(ac["actors"])==2,"ACTOR_COUNT")
    actors=[]
    for actor in ac["actors"]:
        name=actor["name"]
        require(name in ACTORS,"ONLY_FICTIONAL_ACTORS")
        owner=next(r for r in wardrobe["characters"] if r["name"]==name)
        shoes=[r for r in owner["garments"] if r["pack"]=="shoes01"]
        require(len(shoes)==1,"SHOE_SOURCE")
        rig=bpy.data.objects[name+"_MPFBRig"]
        shoe=bpy.data.objects[shoes[0]["native_object"]]
        require(len(rig.data.bones)==163 and any(m.type=="ARMATURE" and m.object==rig for m in shoe.modifiers),
                "NATIVE_SOURCE_SHOE_NOT_SKINNED")
        _,_,starts=actor_plan(actor)
        require(set(starts)==set(SIDES) and all(s is not None for s in starts.values()),"NO_SOURCE_CANDIDATE")
        selected={n for start in starts.values() for n in range(start,start+6)}
        original={}
        for i in range(max(selected)+1):
            seek(i/60)
            if i in selected:original[i]=rig.matrix_world.copy()
        xs=[float(v.co.x) for v in shoe.data.vertices]
        split=(min(xs)+max(xs))/2
        halves={s:[i for i,v in enumerate(xs) if (v>=split)==(s=="L")] for s in SIDES}
        require(all(len(halves[s])>50 for s in SIDES),"MESH_PARTITION")
        tmp=setup(rig,scene,name)
        chain=set(n for s in SIDES for n in tmp[s][3])
        windows=[]
        try:
            for anchor,start in starts.items():
                seek(start/60)
                rig.matrix_world=original[start].copy()
                for side in SIDES:tmp[side][0].influence=0.
                bpy.context.view_layer.update()
                mesh0=mesh_world(shoe)
                ids={s:select_ids(mesh0,halves[s]) for s in SIDES}
                require(all(len(ids[s])>=8 for s in SIDES),"MATERIAL_COHORT_EMPTY")
                for bound in BOUNDS:
                    for mode in MODES:
                        rows=[]
                        for n in range(start,start+6):
                            for side in SIDES:tmp[side][0].influence=0.
                            seek(n/60)
                            rig.matrix_world=original[n].copy()
                            bpy.context.view_layer.update()
                            tails={s:bone_world(rig,"foot."+s,tail=True) for s in SIDES}
                            for s in SIDES:
                                p=bone_world(rig,"foot."+s)
                                expected=actor["sides"][s][n]["target_foot"]
                                require(math.dist(p[:2],expected[:2])<.002,"SOURCE_NULL_BONE_XY_DRIFT")
                            before=observe(rig,shoe,ids,halves)
                            before_z={s:float(bone_world(rig,"foot."+s).z) for s in SIDES}
                            initial_pose=pose(rig,chain)
                            plan=proposal({s:before[s]["min_z_m"] for s in SIDES},bound,mode)
                            check_plan(plan)
                            root=Vector((0.,0.,plan["root_z_m"]))
                            if mode in ("root_z","joint_z"):
                                rig.matrix_world=Matrix.Translation(root)@original[n]
                                bpy.context.view_layer.update()
                            if mode in ("legs_z","joint_z"):
                                for side in SIDES:
                                    ik,target,foot,_=tmp[side]
                                    target.location=tails[side]+root+Vector((0.,0.,plan["leg_z_m"][side]))
                                bpy.context.view_layer.update()
                                for side in SIDES:tmp[side][0].influence=1.
                            bpy.context.view_layer.update()
                            after=observe(rig,shoe,ids,halves)
                            after_z={s:float(bone_world(rig,"foot."+s).z) for s in SIDES}
                            realized={}
                            for s in SIDES:
                                realized[s]=abs(after_z[s]-(before_z[s]+plan["root_z_m"]+plan["leg_z_m"][s]))
                            rows.append({
                                "source_index":n,"source_time_s":n/60,"plan":plan,
                                "source":before,"candidate":after,
                                "source_foot_bone_head_z_m":before_z,
                                "candidate_foot_bone_head_z_m":after_z,
                                "actual_target_bone_vertical_residual_m":realized,
                                "max_fivebone_pose_rotation_rad":shortest(initial_pose,pose(rig,chain)),
                            })
                            for side in SIDES:tmp[side][0].influence=0.
                            rig.matrix_world=original[n].copy()
                            bpy.context.view_layer.update()
                        windows.append({"actor":name,"source_selected_side":anchor,
                                        "first_source_sample":start,"mode":mode,"bound_m":bound,
                                        "reference_ground_z_m":0.0,
                                        "physical_stance_proven":False,
                                        "actual_anatomical_support_proven":False,
                                        "temporal_source_plan":temporal_metrics(rows),
                                        "samples":rows})
        finally:
            clear(tmp)
        actors.append({"actor":name,"windows":windows})
    report={"schema":"scp.n03d-ah.vertical-shoe-actual-native.v1",
            "source_class":"ORIGINAL_FICTIONAL_CC0",
            "source_scene_sha256":a.sha,"source_trace_sha256":digest(a.trace),
            "source_ac_sha256":digest(a.ac),"scene_source_unchanged":True,
            "corrected_animation_saved":False,"true_native_dual_leg_ik_executed":True,
            "physical_stance_proven":False,"floor_reference_calibrated":False,
            "anatomical_heel_ball_toe_verified":False,"independent_visual_review":False,
            "mvp_accepted":False,"actors":actors}
    Path(a.out).write_text(json.dumps(report,sort_keys=True,allow_nan=False)+"\n")
    judged=assess(report)
    Path(a.out+".critic.json").write_text(json.dumps(judged,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("N03D_AH_REAL_NATIVE_VERTICAL_FACTORIAL",json.dumps(judged,sort_keys=True),flush=True)
    require(judged["status"]=="HOLD" and len(judged["windows"])==32,"FORGED_NATIVE_ACCEPTANCE")

if __name__=="__main__":main()
