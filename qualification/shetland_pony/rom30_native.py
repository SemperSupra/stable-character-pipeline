"""Evaluate explicit carpus, stifle and hock, 48 frames, from reimported GLB.

The angle primitive is frozen in independent PR #311, not copied here.
Scientific FAIL does not mean an infrastructure test failed. Never claim
veterinary normal range or actual hoof-ground contact from these limits.
"""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector

def main():
    a=sys.argv[sys.argv.index("--")+1:]
    if len(a)!=3:raise SystemExit("GLB outcome.json independent-metrics-directory")
    source,out,metrics=Path(a[0]),Path(a[1]),Path(a[2])
    sys.path.insert(0,str(metrics))
    from rom_metrics import evaluate_triplet
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    rig=[o for o in bpy.context.scene.objects if o.type=="ARMATURE"]
    if len(rig)!=1:raise RuntimeError("expected one rig")
    arm=rig[0]
    bones={b.name for b in arm.data.bones}
    required={f"{prefix}_{side}_{tail}" for prefix,tail in (("front","forearm"),("hind","stifle")) for side in ("L","R")}
    missing=sorted(required-bones)
    traces={}
    issues=[f"missing_anatomical_chain:{name}" for name in missing]
    if len(bones)!=30:issues.append("expected_exact_30_joint_kinematic_skeleton")
    for side in ("L","R"):
        for joint in ("front_carpus","hind_stifle","hind_hock"):
            key=joint+"_"+side
            observations=[]
            for frame in range(1,49):
                bpy.context.scene.frame_set(frame)
                dg=bpy.context.evaluated_depsgraph_get()
                ar=arm.evaluated_get(dg)
                prefix=joint.split("_")[0]
                def bone(part):
                    return ar.pose.bones.get(prefix+"_"+side+"_"+part)
                if joint=="front_carpus":
                    a,b,c=bone("forearm"),bone("forearm"),bone("lower")
                    pick=lambda: (a.head,b.tail,c.tail)
                    lim=115.
                elif joint=="hind_stifle":
                    a,b,c=bone("upper"),bone("upper"),bone("stifle")
                    pick=lambda: (a.head,b.tail,c.tail)
                    lim=105.
                else:
                    a,b,c=bone("stifle"),bone("stifle"),bone("lower")
                    pick=lambda: (a.head,b.tail,c.tail)
                    lim=130.
                if None in (a,b,c):raise RuntimeError("missing required anatomical bone in reimported GLB")
                pts=[tuple(float(v) for v in (ar.matrix_world @ Vector(p))) for p in pick()]
                metric=evaluate_triplet(*pts)
                observations.append({"frame":frame,"flexion_deg":round(metric["flexion_deg"],5),
                     "lateral_offset_m":round(metric["lateral_offset_m"],6),
                     "bend_sign":metric["sagittal_bend_sign"],
                     "segment_lengths_m":[round(x,6) for x in metric["segment_lengths_m"]]})
            angles=[o["flexion_deg"] for o in observations]
            steps=[abs(angles[i+1]-angles[i]) for i in range(47)]
            maxlengthchange=max(abs(o["segment_lengths_m"][j]-observations[0]["segment_lengths_m"][j])
                                for o in observations for j in (0,1))
            anomalies=[]
            if max(angles)>lim:anomalies.append("unbounded_flexion")
            if max(angles)-min(angles)<3:anomalies.append("immobile_joint")
            if max(steps)>24:anomalies.append("joint_snap_gt24deg_per_frame")
            if max(o["lateral_offset_m"] for o in observations)>.055:anomalies.append("out_of_sagittal_plane")
            if maxlengthchange>.02:anomalies.append("bone_length_not_invariant")
            issues.extend(key+":"+x for x in anomalies)
            traces[key]={"min_deg":min(angles),"max_deg":max(angles),
                         "excursion_deg":round(max(angles)-min(angles),3),
                         "max_step_deg":round(max(steps),3),
                         "max_segment_length_delta_m":round(maxlengthchange,6),
                         "observations":observations,
                         "provisional_max_flexion_deg":lim}
    result={"schema":"equine.rom30.science.v1","source_glb":source.name,
      "actual_rig_joint_count":len(bones),"explicit_joint_names":sorted(required),
      "blender":bpy.app.version_string,"frames":48,"observed_joints":traces,
      "failure_codes":issues,
      "scientific_verdict":"JOINT_ROM_OR_ANATOMY_FAIL" if issues else "ENGINEERING_GUARDRAILS_PASS_BIOLOGY_UNKNOWN",
      "limits":"conservative provisional engineering bounds; not veterinary reference ranges",
      "visual_acceptance":False}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"ROM":result["scientific_verdict"],"failures":issues}))
main()
