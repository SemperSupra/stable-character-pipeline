"""N03D-AK actual Blender source-safe full 24Hz+offgrid 60Hz root world-Z execution.

Physically moves source MPFB armature object in ephemeral Blender session and
reads BOTH actual evaluated original CC0 shoe mesh partitions. No saved action,
Blend or animation. True floor/contact/heel-toe still unknown.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector

HERE=Path(__file__).parent
sys.path.insert(0,str(HERE))
from critic import assess,CHOSEN,SIDES,ACTORS,N24,N60,lerp,require
sys.path.insert(0,str(HERE.parent/"r090-dressed"))
from measure import stable_sole_sample
sys.path.insert(0,str(HERE.parent/"n03d-ai-temporal-floor"))
from temporal import independent as source_independent

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True).encode()).hexdigest()
def seek(t):
    scene=bpy.context.scene
    n=int(math.floor(t*12+1e-8))
    scene.frame_set(n,subframe=t*12-n)
    bpy.context.view_layer.update()
def observe(shoe):
    data=stable_sole_sample(shoe)
    require(set(data)==set(SIDES),"NATIVE_SHOE_SIDES_CHANGED")
    return {s:{"z_m":float(data[s]["z_m"]),
               "xy_m":[float(v) for v in data[s]["xy_m"]]} for s in SIDES}
def source_frames(rig,shoe,rate,count):
    frames=[]
    for i in range(count):
        seek(i/rate)
        frames.append({"matrix":rig.matrix_world.copy(),"shoe":observe(shoe)})
    return frames
def one_clock(rig,shoe,rate,count,source,sequence,limit):
    rows=[]
    for i in range(count):
        t=i/rate
        root=lerp(sequence,t)
        require(root>=-1e-9 and root<=limit+1e-6,"TRIAL_SCHEDULE_ROOT_CAP")
        seek(t)
        rig.matrix_world=source[i]["matrix"].copy()
        bpy.context.view_layer.update()
        # The source is separately captured at same timestamp and rig/matrix.
        rig.matrix_world=Matrix.Translation(Vector((0,0,root)))@source[i]["matrix"]
        bpy.context.view_layer.update()
        after=observe(shoe)
        rig.matrix_world=source[i]["matrix"].copy()
        bpy.context.view_layer.update()
        shoes={}
        for side in SIDES:
            a=source[i]["shoe"][side];b=after[side]
            shoes[side]={"source_z_m":a["z_m"],"candidate_z_m":b["z_m"],
                         "source_xy_m":a["xy_m"],"candidate_xy_m":b["xy_m"]}
        rows.append({"index":i,"time_s":t,"root_world_lift_m":root,"shoes":shoes})
    return rows
def main():
    arg=argparse.ArgumentParser()
    for n in ("scene","sha","wardrobe","retarget","trace","ac","ai","out"):
        arg.add_argument("--"+n,required=True)
    a=arg.parse_args(sys.argv[sys.argv.index("--")+1:])
    require(sha(a.scene)==a.sha,"SOURCE_SCENE_SHA_PIN")
    scene=bpy.context.scene
    require(scene.get("r078_source")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and
            scene.get("r082_wardrobe")=="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL" and
            (scene.frame_start,scene.frame_end,scene.render.fps)==(0,71,12),
            "SOURCE_RIGHTS_OR_TIMEBASE")
    wardrobe=json.loads(Path(a.wardrobe).read_text())
    rec=json.loads(Path(a.retarget).read_text())
    trace=json.loads(Path(a.trace).read_text())
    ac=json.loads(Path(a.ac).read_text())
    ai=json.loads(Path(a.ai).read_text())
    require(rec["candidate_blend_sha256"]==a.sha and
            rec["input_scene_sha256"]==wardrobe["blend_sha256"] and
            trace["source_scene_sha256"]==a.sha and
            ac["source_scene_sha256"]==a.sha and
            ac["source_shoe_trace_sha256"]==sha(a.trace) and
            ai["source_scene_sha256"]==a.sha and
            ai["source_trace_sha256"]==canonical(trace) and
            ai["source_ac_sha256"]==canonical(ac) and
            source_independent(ai)=="HOLD",
            "SOURCE_AI_ACTUAL_TRACE_JOIN")
    require(len(ai["actors"])==2 and
            set(x["actor"] for x in ai["actors"])==set(ACTORS),
            "ORIGINAL_ACTORS_ONLY")
    actors=[]
    for actor in ai["actors"]:
        name=actor["actor"]
        owner=next(x for x in wardrobe["characters"] if x["name"]==name)
        match=[x for x in owner["garments"] if x["pack"]=="shoes01"]
        require(len(match)==1,"SOURCE_CC0_SHOE")
        rig=bpy.data.objects[name+"_MPFBRig"]
        shoe=bpy.data.objects[match[0]["native_object"]]
        require(len(rig.data.bones)==163 and any(m.type=="ARMATURE" and m.object==rig for m in shoe.modifiers),
                "REAL_NATIVELY_SKINNED_SHOE")
        source24=source_frames(rig,shoe,24,N24)
        source60=source_frames(rig,shoe,60,N60)
        true_native=next(x for x in trace["actors"] if x["actor"]==name)
        for i in range(N24):
            for side in SIDES:
                original=true_native["sides"][side]["samples"][i]["z_m"]
                require(abs(source24[i]["shoe"][side]["z_m"]-original)<.002,
                        "SOURCE_NATIVE_24HZ_REPLAY_MISMATCH")
        plans={(x["root_budget_m"],x["root_vertical_slew_mps"]):x for x in actor["trials"]}
        require(set(plans)==set(CHOSEN)|{(.04,.25),(.04,.75)},"PLAN_DOE_CUSTODY")
        trials=[]
        for budget,speed in CHOSEN:
            model=plans[(budget,speed)]
            lift=model["predicted_root_lift_m"]
            require(len(lift)==N24,"LIFT_CLOCK")
            data24=one_clock(rig,shoe,24,N24,source24,lift,budget)
            data60=one_clock(rig,shoe,60,N60,source60,lift,budget)
            trials.append({"budget_m":budget,"slew_mps":speed,
                           "shoe_partitions_are_anatomical":False,
                           "root_only_no_leg_ik":True,
                           "source_ground_is_scene_Z0_only":True,
                           "samples":{"24hz":data24,"60hz":data60}})
        actors.append({"actor":name,"rig_bones":len(rig.data.bones),"trials":trials})
    report={"schema":"scp.n03d-ak.native-lipschitz-root-z.v1",
            "source_class":"ORIGINAL_FICTIONAL_CC0",
            "source_scene_sha256":a.sha,"source_shoe_trace_sha256":sha(a.trace),
            "source_ai_sha256":sha(a.ai),"source_scene_unchanged":True,
            "actual_native_root_world_actuated":True,"root_curve_saved":False,
            "independent_floor_calibration_done":False,
            "anatomical_contact_verified":False,"source_force_proven":False,
            "independent_visual_review":False,"mvp_accepted":False,
            "actors":actors}
    Path(a.out).write_text(json.dumps(report,sort_keys=True,allow_nan=False)+"\n")
    judged=assess(report)
    Path(a.out+".critic.json").write_text(json.dumps(judged,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("N03D_AK_ACTUAL_NATIVE_FULLCLIP_24_60HZ_ROOT_LIFT",
          json.dumps({"status":judged["status"],"trials":[{"actor":v["actor"],
                    "budget_m":v["budget_m"],"slew_mps":v["slew_mps"],
                    "lift_m":v["max_actual_root_lift_m"],
                    "mismatch_m":v["max_actual_vertical_rigid_translation_mismatch_m"],
                    "source_to_reality":v["actual_24_and_offgrid_60hz_shoes"]} for v in judged["trials"]]},sort_keys=True),flush=True)
    require(judged["status"]=="HOLD" and len(judged["trials"])==8,"FORGED_GAIT_RELEASE")

if __name__=="__main__":main()
