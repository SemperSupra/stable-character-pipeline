"""N03D-BA true Blender 5.2.4 native import / rig skin / walk-state witness.

Not a substitute for matching the same source 100STYLE or anatomical contacts.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy

def require(ok,why):
    if not ok:raise ValueError(why)
def tohash(xs):
    return hashlib.sha256(json.dumps(xs,sort_keys=True,default=str).encode()).hexdigest()
def active_walk():
    """Request exact 'walk' NLA strip across imported glTF objects when present."""
    seen=[]
    for obj in bpy.data.objects:
        an=obj.animation_data
        if not an:continue
        matches=[]
        for track in an.nla_tracks:
            for strip in track.strips:
                if strip.action and strip.action.name.lower() in ("walk","walkaction","walk.001"):
                    matches.append((track,strip))
        if matches:
            selected=matches[0][0]
            for track in an.nla_tracks:
                track.mute=track!=selected
            seen.append({"object":obj.name,"strip":matches[0][1].name,"action":matches[0][1].action.name})
    return seen
def observed_mesh(obj):
    eval_obj=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=eval_obj.to_mesh()
    try:
        count=len(mesh.vertices)
        require(count>0,"NO_NATIVE_EVALUATED_MESH")
        stride=max(1,count//1000)
        verts=[tuple(round(float(v),6) for v in (eval_obj.matrix_world@mesh.vertices[i].co))
               for i in range(0,count,stride)]
        require(all(all(math.isfinite(c) for c in q) for q in verts),"NATIVE_NONFINITE_VERTICES")
        return {"evaluated_vertices":count,"sample_digest":tohash(verts),"sampled_points":len(verts),
                "min_sample_z_m":round(min(v[2] for v in verts),6),
                "max_sample_z_m":round(max(v[2] for v in verts),6)}
    finally:eval_obj.to_mesh_clear()
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--model",required=True);a.add_argument("--candidate",required=True)
    a.add_argument("--source-audit",required=True);a.add_argument("--output",required=True)
    args=a.parse_args(sys.argv[sys.argv.index("--")+1:])
    audit=json.loads(Path(args.source_audit).read_text())
    require(audit.get("candidate")==args.candidate and
            audit.get("status")=="SOURCE_BYTES_VERIFIED_STRUCTURAL_ONLY_HOLD" and
            audit.get("production_admitted") is False and
            audit.get("physical_contact_accepted") is False,
            "UNADMITTED_INPUT")
    require(hashlib.sha256(Path(args.model).read_bytes()).hexdigest()==
            audit["assets"]["model"]["sha256"],"SOURCE_MODEL_SHA_MISMATCH")
    if args.model.endswith(".blend"):
        bpy.ops.wm.open_mainfile(filepath=str(Path(args.model).resolve()))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(Path(args.model).resolve()),import_shading="NORMALS")
    rigs=sorted([obj for obj in bpy.data.objects if obj.type=="ARMATURE"],key=lambda r:r.name)
    skinned=sorted([o for o in bpy.data.objects if o.type=="MESH" and
                    any(m.type=="ARMATURE" and m.object and m.object in rigs for m in o.modifiers)],
                   key=lambda m:m.name)
    act=sorted(a.name for a in bpy.data.actions)
    walk=active_walk()
    all_actions=[{"name":a.name,"first":float(a.frame_range[0]),"last":float(a.frame_range[1])}
                 for a in bpy.data.actions]
    end=min(240,max([a["last"] for a in all_actions]+[float(bpy.context.scene.frame_end),24.]))
    first=min(1.,min([a["first"] for a in all_actions]+[1.]))
    frames=sorted(set(int(first+(end-first)*t/4) for t in range(5)))
    telemetry=[]
    if rigs and skinned:
        mesh=skinned[0]
        for frame in frames:
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            rig_data=[{"name":rig.name,"joint_count":len(rig.data.bones),
                       "pose_sha256":tohash([tuple(round(float(q),6) for row in bone.matrix for q in row)
                                            for bone in rig.pose.bones])}
                      for rig in rigs]
            telemetry.append({"frame":frame,"rigs":rig_data,
                              "real_evaluated_skin":observed_mesh(mesh)})
    movement=(len(set(t["real_evaluated_skin"]["sample_digest"] for t in telemetry))>1
              if telemetry else False)
    joint_movement=(any(len(set(t["rigs"][idx]["pose_sha256"] for t in telemetry))>1
                        for idx in range(len(rigs))) if telemetry else False)
    result={"schema":"scp.n03d-ba.blender-native-admission.v1",
            "candidate":args.candidate,"source_commit":audit["source_commit"],
            "source_model_sha256":audit["assets"]["model"]["sha256"],
            "blender_version":list(bpy.app.version),
            "rig_count":len(rigs),"skinned_mesh_count":len(skinned),
            "bone_counts":[len(r.data.bones) for r in rigs],
            "action_names":act,"nla_selected_walk":walk,
            "foot_named_bones":[r.name+":"+b.name for r in rigs for b in r.data.bones
                                 if any(x in b.name.lower() for x in ("foot","toe","ball","ankle"))][:80],
            "native_frames":frames,"telemetry":telemetry,
            "evaluated_skin_changed":movement,"evaluated_pose_changed":joint_movement,
            "native_skin_import_verified":bool(rigs and skinned),
            "native_walk_clip_qualified":bool(rigs and skinned and walk and movement and joint_movement),
            "actual_heel_ball_toe_contact_measured":False,
            "source_motion_matched_to_100style":False,
            "physical_gait_accepted":False,"mvp_accepted":False,
            "status":"PASS_NARROW_NATIVE_WALK" if rigs and skinned and walk and movement and joint_movement
            else ("PASS_NARROW_SKIN_ONLY" if rigs and skinned else "HOLD_IMPORT_OR_SKIN")}
    require(result["blender_version"]==[5,2,4],"BLENDER_PIN_CHANGED")
    require(result["physical_gait_accepted"] is False and result["mvp_accepted"] is False,
            "FALSE_PHYSICAL_RELEASE")
    Path(args.output).write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("N03D_BA_TRUE_BLENDER_NATIVE_WITNESS",json.dumps({k:v for k,v in result.items()
          if k not in ("telemetry","foot_named_bones")},sort_keys=True),flush=True)
if __name__=="__main__":main()
