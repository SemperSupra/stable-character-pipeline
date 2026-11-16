"""R044 independent morph DOE + synthetic organ co-export on editable MPFB model.

Exact pinned official MPFB, original synthetic organ proxies, independent
public CPU Blender process. Source .blend stays immutable and models never
leave disposable runner. No claim of real organ registration or film readiness.
"""
import argparse
import importlib.util
import json
import math
import os
import sys

import bpy

sys.path.insert(0,os.path.dirname(__file__))
import morph_mask_preserving as core

FRAMES=(1,12,24)
LIMIT_M=0.00008
ORGAN_LIMIT_M=0.00015

def fail(reason):
    raise RuntimeError("R044_MORPH_ORGAN_HOLD "+reason)

def keys(obj):
    if obj.data.shape_keys is None: fail("expected editable shape keys on "+obj.name)
    return obj.data.shape_keys.key_blocks

def test_points(reference,challenger,frame,limit,title):
    x=core.evaluated(reference,frame)
    y=core.evaluated(challenger,frame)
    d1=core.nearest(x,y)
    d2=core.nearest(y,x)
    max_err=max(d1["max_m"],d2["max_m"])
    if max_err>limit: fail(title+" frame "+str(frame)+" geometry error "+str(max_err))
    return max_err

def test_visibility(obj,body,frame):
    bpy.context.scene.frame_set(frame)
    a=core.evaluated(body,frame)
    b=core.evaluated(obj,frame)
    original=bool(obj.hide_render)
    try:
        obj.hide_render=not original
        b2=core.evaluated(obj,frame)
        a2=core.evaluated(body,frame)
        if len(b)!=len(b2) or any((u-v).length>1e-9 for u,v in zip(b,b2)):
            fail("visibility toggle mutated organ evaluated state: "+obj.name)
        if len(a)!=len(a2) or any((u-v).length>1e-9 for u,v in zip(a,a2)):
            fail("visibility toggle mutated external skin state")
    finally:
        obj.hide_render=original

def imported_scene(derived,rig,organs,out):
    output=os.path.join(out,"r044-morph-organ-allweights.glb")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [derived,rig]+organs: obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.gltf(filepath=output,export_format="GLB",
        use_selection=True,export_all_influences=True,export_morph=True)
    if not os.path.isfile(output) or os.stat(output).st_size<5000:
        fail("no actual organ integrated GLB")
    before={o.as_pointer() for o in bpy.data.objects}
    bpy.ops.import_scene.gltf(filepath=output)
    added=[o for o in bpy.data.objects if o.as_pointer() not in before]
    arms=[o for o in added if o.type=="ARMATURE"]
    if len(arms)!=1 or len(arms[0].data.bones)!=len(rig.data.bones):
        fail("imported org/body pack rig not stable")
    bodies=[o for o in added if o.type=="MESH" and "R043_EditableMask_MPFB_Body" in o.name]
    if len(bodies)!=1: fail("imported derived body missing or duplicated")
    body=bodies[0]
    if len(keys(body))!=len(keys(derived)):
        fail("imported body lost morph controls")
    if [k.name for k in keys(body)]!=[k.name for k in keys(derived)]:
        fail("imported body morph control names reordered")
    if not any(m.type=="ARMATURE" and m.object in arms for m in body.modifiers):
        fail("body rig skin not imported")
    matches=[]
    for source in organs:
        cand=[o for o in added if o.type=="MESH" and source.name in o.name]
        if len(cand)!=1: fail("imported organ proxy missing or duplicate: "+source.name)
        if not any(m.type=="ARMATURE" and m.object in arms for m in cand[0].modifiers):
            fail("imported synthetic organ lost armature: "+source.name)
        matches.append(cand[0])
    return body,matches,{"sha256":core.hfile(output),"bytes":os.stat(output).st_size,
        "imported_rig_bones":len(arms[0].data.bones),
        "imported_body_vertices":len(body.data.vertices),
        "imported_morph_keys":[k.name for k in keys(body)],
        "imported_synthetic_organs":[x.name for x in matches]}

def variants(meta):
    controls=[x for x in meta if x["name"]!="Basis" and not x["mute"]]
    if len(controls)!=8: fail("expected eight source controls in this pinned fixture")
    reps=[]
    def offset(x,delta):
        return min(x["slider_max"],max(x["slider_min"],x["value"]+delta))
    for entry in controls:
        v=offset(entry,+.09)
        if abs(v-entry["value"])<.005: v=offset(entry,-.09)
        if abs(v-entry["value"])<.005: fail("unmovable source control")
        reps.append(("single:"+entry["name"],{entry["name"]:v}))
    paired={}
    alternate={}
    for i,k in enumerate(controls):
        paired[k["name"]]=offset(k,.04)
        alternate[k["name"]]=offset(k,.07 if i%2==0 else -.07)
    reps.extend([("multi:uniform",paired),("multi:alternate",alternate)])
    return reps

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True)
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    root=os.path.abspath(args.out)
    blend=os.path.join(root,"mpfb-official-anatomy.blend")
    if not os.path.isfile(blend): fail("source blend absent")
    original_hash=core.hfile(blend)
    body=bpy.data.objects.get("R036_Official_MPFB_Human")
    rig=bpy.data.objects.get("R036_Official_MPFB_Rig")
    originals=[bpy.data.objects.get("R036_AnatomyProxy_Left"),
               bpy.data.objects.get("R036_AnatomyProxy_Right")]
    if not body or not rig or any(x is None for x in originals):
        fail("native original body/rig/synthetic anatomy absent")
    source_meta=core.keymeta(body)
    derived,struct=core.remap_editable(body,rig)
    imported,imported_orgs,pack=imported_scene(derived,rig,originals,root)
    all_objects=(body,derived,imported)
    key_values={entry["name"]:entry["value"] for entry in source_meta if entry["name"]!="Basis"}
    results=[]
    baseline=None
    try:
        all_variants=[("baseline",{})]+variants(source_meta)
        for label,changes in all_variants:
            for obj in all_objects:
                for name,value in key_values.items():
                    keys(obj)[name].value=changes.get(name,value)
            body_max=0.0
            clone_max=0.0
            organ_max=0.0
            for f in FRAMES:
                clone_max=max(clone_max,test_points(body,derived,f,1e-5,"source-derived skin"))
                body_max=max(body_max,test_points(body,imported,f,LIMIT_M,"imported visible body"))
                for src,dst in zip(originals,imported_orgs):
                    organ_max=max(organ_max,test_points(src,dst,f,ORGAN_LIMIT_M,"imported synthetic organ "+src.name))
            results.append({"variant":label,"modified_shape_keys":len(changes),
                "max_native_vs_derived_m":clone_max,
                "max_native_vs_imported_m":body_max,
                "max_synthetic_organs_native_vs_imported_m":organ_max})
            if label=="baseline": baseline=results[-1]
    finally:
        for obj in all_objects:
            for name,value in key_values.items(): keys(obj)[name].value=value
    if core.keymeta(body)!=source_meta:
        fail("source morph metadata changed following DOE")
    if original_hash!=core.hfile(blend): fail("saved source mutated")
    for src in originals:
        for f in (1,24): test_visibility(src,body,f)
    for obj in (body,derived):
        if len(keys(obj))!=len(source_meta):
            fail("source or derived lost shape controls")
    if any(row["max_native_vs_imported_m"]>LIMIT_M for row in results):
        fail("some parametric morph failed import")
    record={
        "schema":"r044.mpfb.morph-synthetic-organs.v1",
        "status":"PASS_NARROW_MULTIMORPH_AND_SYNTHETIC_ORGAN_COEXPORT",
        "source_sha256":original_hash,"source_unchanged":True,
        "variants_checked":len(results),
        "frames":list(FRAMES),
        "source_shape_key_blocks":len(source_meta),
        "native_organ_proxy_count":len(originals),
        "native_skin_vertices":len(core.evaluated(body,1)),
        "mask_remap":struct,"coexport":pack,"results":results,
        "limits":"Only generic MPFB and synthetic ellipsoids; no native registered organs, physical tissue, real engine, photos, character identity, game/film or human preference approval",
        "decision":"HOLD_PRODUCT_RELEASE",
    }
    with open(os.path.join(root,"r044-morph-organ-doe.json"),"w",encoding="utf-8") as handle:
        json.dump(record,handle,indent=2,sort_keys=True)
    print("R044_MORPH_ORGAN_DOE "+json.dumps(record,sort_keys=True))

if __name__=="__main__":
    main()
