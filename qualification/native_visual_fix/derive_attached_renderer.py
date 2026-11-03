#!/usr/bin/env python3
"""Deterministic source-safe derived native renderer for spatial attachment falsification.

Read-only pinned #263 producer; modifies exactly one original-synthetic mesh
parenting line and one additive native observer. Never touches original owner
branch or generates human likeness, human ROM/contact, or protected media.
"""
import argparse,hashlib,json,pathlib,subprocess,sys
PIN_BLOB="ea2756f9d4a0636e75a6069afe72b819dac3a1ee"
PIN_COMMIT="a6f9d44d8638e35ad9fd8258753fac3baf3a0c40"
NEEDLE='    scene.collection.objects.link(ob);mesh.materials.append(palette[actor])'
REPLACE='    scene.collection.objects.link(ob);mesh.materials.append(palette[actor])\n    ob.parent=arm  # same spatial transform as original actor armature; not shared with source-owner'
ANCHOR='    r[actor]["rewind_error_m"]=rewind'
ADDITIONAL='''    # Independent spatial/source cross-join: actual evaluated skin must
    # follow the same original authored actor ROOT as its visible surrogate.
    # Check multiple real frames, not only nonfrozen vertex displacement.
    root_offsets={}
    for testframe in (0,12,36,60,71):
        scene.frame_set(testframe)
        bpy.context.view_layer.update()
        ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh_eval=ev.to_mesh()
        try:
            x_center=sum(float((ev.matrix_world@vert.co).x) for vert in mesh_eval.vertices)/len(mesh_eval.vertices)
        finally:ev.to_mesh_clear()
        source_root=trace["frames"][testframe]["actors"][actor]["root_x_m"]
        offset=abs(x_center-source_root)
        if not math.isfinite(offset) or offset>.38:
            raise RuntimeError("DETACHED_HIERARCHICAL_SKIN_FROM_VISIBLE_ACTOR:"+actor+":"+str(testframe)+":"+str(offset))
        root_offsets[str(testframe)]=offset
    r[actor]["actual_source_root_max_lateral_error_m"]=max(root_offsets.values())
    r[actor]["source_root_audit_frames"]=[0,12,36,60,71]
    r[actor]["mesh_spatial_parent_is_actor_armature"]=ob.parent==arm
    if not r[actor]["mesh_spatial_parent_is_actor_armature"]:
        raise RuntimeError("MESH_ACTOR_PARENT_CONNECTION_MISSING")
'''
def run():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--receipt",required=True)
    a=p.parse_args()
    source=pathlib.Path(a.source)
    original=source.read_text()
    got=subprocess.check_output(["git","hash-object",str(source)],text=True).strip()
    if got!=PIN_BLOB or original.count(NEEDLE)!=1 or original.count(ANCHOR)!=1:
        raise SystemExit("UNPINNED_OR_AMBIGUOUS_NATIVE_SOURCE")
    after=original.replace(NEEDLE,REPLACE,1).replace(ANCHOR,ANCHOR+"\n"+ADDITIONAL,1)
    if after==original:raise SystemExit("VISUAL_ATTACHMENT_PATCH_NOT_APPLIED")
    output=pathlib.Path(a.out);receipt=pathlib.Path(a.receipt)
    if source.resolve()==output.resolve() or output.exists() or receipt.exists():
        raise SystemExit("REFUSE_MODIFY_OWNER_OR_OVERWRITE")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(after,encoding="utf8")
    report={"schema":"scp.r009.original-synthetic-derived-native-attachment-patch.v1",
      "original_source_git_blob":got,"original_owner_head":PIN_COMMIT,
      "derived_native_sha256":hashlib.sha256(after.encode()).hexdigest(),
      "scope":"REVIEWER_PARENT_MESH_TO_ACTOR_RIG_AND_OBSERVE_5_SOURCE_ROOT_FRAMES",
      "fixture_only":True,"source_rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
      "biological_rom":"UNKNOWN","real_ground_contact":"UNKNOWN",
      "protected_R009":"HELD_NOT_ACCEPTED"}
    with receipt.open("x") as f:json.dump(report,f,sort_keys=True,indent=2);f.write("\n")
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":run()
