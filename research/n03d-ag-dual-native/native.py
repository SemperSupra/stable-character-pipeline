"""N03D-AG: REAL simultaneous root and bilateral five-bone Blender IK actuation.

$0 public original-only scene. All modes are measured in native evaluated
skinned CC0 footwear, compared on matched SOURCE-selected heldout 60Hz samples.
This does not establish anatomical correspondence or acceptable stance.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path

import bpy
from mathutils import Matrix,Vector

HERE=Path(__file__).parent
sys.path.insert(0,str(HERE))
from plan import MODES,BOUNDS,ACTORS,SIDES,actor_plan,corrections,independent_plan,require
sys.path.insert(0,str(HERE.parent/"n03d-y-material"))
from material import select_ids
sys.path.insert(0,str(HERE.parent/"n03d-ag-dual-native"))
from critic import assess

def sha(x):
    return hashlib.sha256(Path(x).read_bytes()).hexdigest()

def seek(t):
    frame=t*12
    i=int(math.floor(frame+1e-8))
    bpy.context.scene.frame_set(i,subframe=frame-i)
    bpy.context.view_layer.update()

def mesh_world(shoe):
    obj=shoe.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m=obj.to_mesh()
    try:
        require(len(m.vertices)==len(shoe.data.vertices),"EVALUATED_SHOE_TOPOLOGY_CHANGED")
        return [tuple(float(q) for q in obj.matrix_world@v.co) for v in m.vertices]
    finally:
        obj.to_mesh_clear()

def bone_world(rig,name,tail=False):
    b=rig.pose.bones[name]
    return (rig.matrix_world@(b.tail if tail else b.head)).copy()

def shortest(a,b):
    vals=[]
    for bone in a:
        x,y=a[bone],b[bone]
        dot=abs(float(x.normalized().dot(y.normalized())))
        vals.append(2*math.acos(min(1.,max(0.,dot))))
    return max(vals)

def pose(rig,names):
    obj=rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return {n:obj.pose.bones[n].matrix.to_quaternion().copy() for n in names}

def observe(rig,shoe,ids,half):
    world=mesh_world(shoe)
    result={}
    for side in SIDES:
        pts=[world[i] for i in ids[side]]
        xy=[sum(p[k] for p in pts)/len(pts) for k in (0,1)]
        result[side]={"bone_head_xy_m":list(bone_world(rig,"foot."+side)[:2]),
                      "material_xy_m":xy,
                      "min_z_m":min(world[i][2] for i in half[side])}
    return result

def setup(rig,scene,name):
    tmp={}
    for side in SIDES:
        foot=rig.pose.bones["foot."+side]
        chain=[n+"."+side for n in ("foot","lowerleg02","lowerleg01","upperleg02","upperleg01")]
        require(all(n in rig.pose.bones for n in chain),"FIVE_BONE_MISSING")
        require(all(rig.data.bones[chain[j]].parent.name==chain[j+1] for j in range(4)),"INVALID_KINEMATIC_CHAIN")
        target=bpy.data.objects.new("N03D_AG_ephemeral_"+name+side,None)
        scene.collection.objects.link(target)
        ik=foot.constraints.new("IK")
        ik.target=target
        ik.chain_count=5;ik.iterations=100;ik.use_stretch=False
        ik.use_rotation=False;ik.use_location=True;ik.influence=0
        tmp[side]=(ik,target,foot,chain)
    return tmp

def clear(tmp):
    for side in SIDES:
        ik,target,foot,_=tmp[side]
        foot.constraints.remove(ik)
        bpy.data.objects.remove(target,do_unlink=True)
    bpy.context.view_layer.update()

def main():
    p=argparse.ArgumentParser()
    for n in ("scene","sha","wardrobe","retarget","trace","ac","out"):
        p.add_argument("--"+n,required=True)
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    require(sha(a.scene)==a.sha,"SOURCE_SCENE_SHA")
    scene=bpy.context.scene
    require(scene.get("r078_source")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and
            scene.get("r082_wardrobe")=="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL","RIGHTS_ORIGINAL_ONLY")
    require((scene.frame_start,scene.frame_end,scene.render.fps)==(0,71,12),"SCENE_TIMEBASE")
    wardrobe=json.loads(Path(a.wardrobe).read_text())
    retarget=json.loads(Path(a.retarget).read_text())
    trace=json.loads(Path(a.trace).read_text())
    ac=json.loads(Path(a.ac).read_text())
    require(retarget["candidate_blend_sha256"]==a.sha and
            retarget["input_scene_sha256"]==wardrobe["blend_sha256"] and
            trace["source_scene_sha256"]==a.sha and
            ac["source_scene_sha256"]==a.sha and
            ac["source_shoe_trace_sha256"]==sha(a.trace),"SOURCE_SHA_JOIN")
    require(ac["schema"]=="scp.n03d-ac.matched-source-to-bone-60hz.v1"
            and len(ac["actors"])==2 and ac["timebase_hz"]==60,"MATCHED_SOURCE_TIMEBASE")
    results=[]
    for actor in ac["actors"]:
        name=actor["name"]
        require(name in ACTORS,"ONLY_ORIGINAL_CHARACTERS")
        owner=next(x for x in wardrobe["characters"] if x["name"]==name)
        shoes=[x for x in owner["garments"] if x["pack"]=="shoes01"]
        require(len(shoes)==1,"SOURCE_SHOE_RIGHTS")
        rig=bpy.data.objects[name+"_MPFBRig"]
        shoe=bpy.data.objects[shoes[0]["native_object"]]
        require(len(rig.data.bones)==163 and any(m.type=="ARMATURE" and m.object==rig for m in shoe.modifiers),"REAL_NATIVE_RIG_SHOE")
        _,paths,starts=actor_plan(actor)
        require(all(s is not None for s in starts.values()),"SOURCE_ELIGIBLE_WINDOW_MISSING")
        selected={i for start in starts.values() for i in range(start,start+6)}
        # Collect 60Hz historical Blender armature WORLD transforms read-only once
        # before installing any temporary IK; source snapshots are a strict null
        # for every subsequent intervention, preventing world-transform leakage.
        sources={}
        for n in range(max(selected)+1):
            seek(n/60)
            if n in selected:
                sources[n]=rig.matrix_world.copy()
        rest_x=[v.co.x for v in shoe.data.vertices]
        midpoint=(min(rest_x)+max(rest_x))*.5
        halves={s:[i for i,x in enumerate(rest_x) if (x>=midpoint)==(s=="L")] for s in SIDES}
        require(all(len(x)>50 for x in halves.values()),"CC0_SHOE_PARTITION")
        windows=[]
        tmp=setup(rig,scene,name)
        all_chain=list({n for s in SIDES for n in tmp[s][3]})
        try:
            for selected_side,start in starts.items():
                seek(start/60)
                rig.matrix_world=sources[start].copy()
                for s in SIDES:tmp[s][0].influence=0
                bpy.context.view_layer.update()
                source_mesh=mesh_world(shoe)
                ids={s:select_ids(source_mesh,halves[s]) for s in SIDES}
                require(all(len(v)>=8 for v in ids.values()),"NO_STABLE_SHOE_POINTS")
                for bound in BOUNDS:
                    for mode in MODES:
                        rows=[]
                        for n in range(start,start+6):
                            for side in SIDES:tmp[side][0].influence=0
                            seek(n/60)
                            rig.matrix_world=sources[n].copy()
                            bpy.context.view_layer.update()
                            # Baseline target foot head checked directly against
                            # the earlier AC native observer on exact same scene.
                            baseline={}
                            tails={}
                            for side in SIDES:
                                foot=bone_world(rig,"foot."+side)
                                expected=actor["sides"][side][n]["target_foot"]
                                require(math.dist(foot[:2],expected[:2])<.002,
                                        "SOURCE_BASELINE_FOOT_NULL_DRIFT")
                                baseline[side]=foot.copy()
                                tails[side]=bone_world(rig,"foot."+side,tail=True)
                            before=observe(rig,shoe,ids,halves)
                            pose0=pose(rig,all_chain)
                            plan=corrections(actor,paths,n,mode,bound)
                            independent_plan(plan)
                            root=Vector((*plan["root_delta_xy_m"],0.))
                            if mode in ("root_only","joint"):
                                rig.matrix_world=Matrix.Translation(root)@sources[n]
                                bpy.context.view_layer.update()
                            if mode in ("leg_only","joint"):
                                for side in SIDES:
                                    ik,target,foot,_=tmp[side]
                                    leg=Vector((*plan["leg"][side]["delta_xy_m"],0.))
                                    target.location=tails[side]+root+leg
                                bpy.context.view_layer.update()
                                for side in SIDES:tmp[side][0].influence=1.
                            bpy.context.view_layer.update()
                            after=observe(rig,shoe,ids,halves)
                            pose_change=shortest(pose0,pose(rig,all_chain))
                            errors={}
                            for side in SIDES:
                                intended=[baseline[side][k]+root[k]+plan["leg"][side]["delta_xy_m"][k] for k in (0,1)]
                                errors[side]=math.dist(after[side]["bone_head_xy_m"],intended)
                            rows.append({
                                "source_index":n,"source_time_s":n/60,
                                "plan":plan,"source":before,"candidate":after,
                                "actual_target_foot_head_residual_xy_m":errors,
                                "max_native_five_bone_pose_delta_rad":pose_change,
                            })
                            for side in SIDES:tmp[side][0].influence=0.
                            rig.matrix_world=sources[n].copy()
                            bpy.context.view_layer.update()
                        windows.append({"actor":name,"source_selected_side":selected_side,
                                        "first_source_sample":start,"mode":mode,"bound_m":bound,
                                        "source_contact_proven":False,"heel_toe_anatomy_verified":False,
                                        "real_native_both_legs_installed":True,"samples":rows})
        finally:
            clear(tmp)
            for side in SIDES:pass
        results.append({"actor":name,"windows":windows})
    output={
        "schema":"scp.n03d-ag.actual-dual-leg-native-factorial.v1",
        "source_class":"ORIGINAL_FICTIONAL_CC0","source_scene_sha256":a.sha,
        "source_trace_sha256":sha(a.trace),"source_ac_sha256":sha(a.ac),
        "source_motion_changed":False,"corrected_blend_saved":False,
        "native_5bone_and_root_actuators_executed":True,
        "source_stance_proven":False,"anatomical_foot_correspondence_proven":False,
        "independent_visual_review_completed":False,"mvp_accepted":False,
        "actors":results}
    Path(a.out).write_text(json.dumps(output,sort_keys=True,allow_nan=False)+"\n")
    verdict=assess(output)
    Path(a.out+".critic.json").write_text(json.dumps(verdict,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("N03D_AG_ACTUAL_NATIVE_ROOT_BILATERAL_FIVEBONE",json.dumps(verdict,sort_keys=True),flush=True)
    require(verdict["status"]=="HOLD" and len(verdict["windows"])==32,"FALSE_NATIVE_ACCEPTANCE")

if __name__=="__main__":main()
