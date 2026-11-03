#!/usr/bin/env python3
"""Pinned, reversible original-synthetic all-72 native spatial lockstep derivative.

This reviewer composes *only* the isolated #267 attachment patch with an
all-frame direct bpy evaluated-mesh/root oracle and a physical spatial-detach
negative. Original source and identity remain unmodified/unadmitted.
"""
import argparse,hashlib,json,pathlib,subprocess
PIN_BLOB="2fbfe79ceb563f88959a5271202ed105e339fa0f"
PIN_PARENT="3b6cb5f1ae6d78159bc5ee718545ed0a80242436"
old_frame="for testframe in (0,12,36,60,71):"
old_receipt='r[actor]["source_root_audit_frames"]=[0,12,36,60,71]'
old_range='not math.isfinite(offset) or offset>.38'
old_end='''    if not r[actor]["mesh_spatial_parent_is_actor_armature"]:
        raise RuntimeError("MESH_ACTOR_PARENT_CONNECTION_MISSING")
'''
extra='''    # Native physical negative: detach by +1.5m *inside Blender*, not by
    # forging source JSON. The identical spatial oracle must reject.
    old_delta=ob.location.x
    scene.frame_set(36)
    ob.location.x=old_delta+1.5
    bpy.context.view_layer.update()
    ev_bad=ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me_bad=ev_bad.to_mesh()
    try:
        x_bad=sum(float((ev_bad.matrix_world@vert.co).x) for vert in me_bad.vertices)/len(me_bad.vertices)
    finally:ev_bad.to_mesh_clear()
    expected=trace["frames"][36]["actors"][actor]["root_x_m"]
    bad_offset=abs(x_bad-expected)
    if not math.isfinite(bad_offset) or bad_offset<=.2:
        raise RuntimeError("SPATIAL_DETACH_MUTANT_FALSE_ACCEPT:"+actor+":"+str(bad_offset))
    ob.location.x=old_delta
    bpy.context.view_layer.update()
    r[actor]["actual_spatial_detach_mutant_rejected"]=True
    r[actor]["detached_mutant_lateral_error_m"]=bad_offset
    r[actor]["source_spatial_audit_frames"]=72
'''
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base",required=True);p.add_argument("--out",required=True);p.add_argument("--receipt",required=True)
    a=p.parse_args()
    base=pathlib.Path(a.base);out=pathlib.Path(a.out);rec=pathlib.Path(a.receipt)
    if out.exists() or rec.exists() or base.resolve()==out.resolve():raise SystemExit("NO_OVERWRITE_AND_NO_OWNER_MUTATION")
    got=subprocess.check_output(["git","hash-object",str(base)],text=True).strip()
    if got!=PIN_BLOB:raise SystemExit("DERIVED_PARENT_BLOB_DRIFT")
    text=base.read_text()
    for old in (old_frame,old_receipt,old_range,old_end):
        if text.count(old)!=1:raise SystemExit("UNSAFE_AMBIGUOUS_PATCH:"+old)
    text=text.replace(old_frame,"for testframe in range(72):",1)
    text=text.replace(old_receipt,'r[actor]["source_root_audit_frames"]=list(range(72))',1)
    text=text.replace(old_range,'not math.isfinite(offset) or offset>.2',1)
    text=text.replace(old_end,old_end+extra,1)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(text,encoding="utf8")
    report={"schema":"scp.r009.authored-synthetic-all72-spatial-lockstep-derivation.v1",
            "status":"SOURCE_ONLY_PINNED_DERIVATION_NOT_NATIVE_ACCEPTANCE",
            "parent_git_blob":got,"parent_commit":PIN_PARENT,
            "derived_sha256":hashlib.sha256(text.encode()).hexdigest(),
            "changes":["all_72_frames_instead_of_5","tighten_actor_root_x_to_0.2m",
                       "native_1.5m_mesh_detachment_must_reject"],
            "source_rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
            "protected_R009":"HELD_NOT_ACCEPTED","human_contact_ROM":"UNKNOWN"}
    with rec.open("x") as f:json.dump(report,f,sort_keys=True,indent=2);f.write("\n")
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":main()
