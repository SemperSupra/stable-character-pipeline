"""Compare independently measured official visible-body source morph effectiveness
against actual source glTF POSITION target buffer effectiveness. Stdlib only.
"""
import argparse
import json
import math
from pathlib import Path
from gltf_godot_morph_compare import expected_morph_arrays, parse_glb

def hold(reason):raise RuntimeError("R051_MORPH_LINEAGE_HOLD "+reason)

def classify(raw_source,glb_effective):
    src=bool(raw_source)
    dst=bool(glb_effective)
    if src and not dst:return "SOURCE_EFFECTIVE_EXPORT_TARGET_ZERO_HOLD"
    if dst and not src:return "SOURCE_ZERO_EXPORT_TARGET_NONZERO_HOLD"
    return "SOURCE_AND_GLTF_EFFECTIVENESS_AGREE"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--glb",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    source=json.loads(Path(args.source).read_text(encoding="utf-8"))
    if source.get("schema")!="r051.native-mpfb.source-morph-effectiveness.v1":
        hold("native source morph audit receipt missing")
    src=source["source_relative_keys"]
    base,arrays=expected_morph_arrays(args.glb)
    if len(src)!=8 or len(arrays)!=8:hold("eight source and eight glTF morph targets required")
    m,blob=parse_glb(args.glb)
    meshes=[m["meshes"][n["mesh"]] for n in m["nodes"]
            if "R043_EditableMask_MPFB_Body" in n.get("name","") and "mesh" in n]
    if len(meshes)!=1:hold("unambiguous body GLB source missing")
    names=meshes[0].get("extras",{}).get("targetNames",[])
    if len(names)!=8 or names!=[x["name"] for x in src]:
        hold("cannot establish source Blender and actual GLB target names/order: "+
             repr(names[:8]))
    rows=[]
    for i,(a,b) in enumerate(zip(src,arrays)):
        max_glb=max(math.sqrt(sum(x*x for x in v)) for v in b)
        effective=max_glb>1e-7
        compared=classify(a["raw_key_effective_on_evaluated_visible_surface"],effective)
        rows.append({"index":i,"source_name":a["name"],
           "source_visible_nonzero_points":a["visible_nonzero_points"],
           "source_visible_max_relative_displacement_m":a["max_visible_relative_displacement_m"],
           "source_hidden_max_relative_displacement_m":a["max_hidden_relative_displacement_m"],
           "actual_glb_morph_max_displacement_m":max_glb,
           "actual_glb_effective":effective,"effectiveness_class":compared})
    mismatches=[r["index"] for r in rows if r["effectiveness_class"]!="SOURCE_AND_GLTF_EFFECTIVENESS_AGREE"]
    if classify(True,False)!="SOURCE_EFFECTIVE_EXPORT_TARGET_ZERO_HOLD":
        hold("source/export negative oracle defective")
    result={"schema":"r051.native-to-gltf-morph-zero-lineage.v1",
       "status":"PASS_NARROW_MORPH_EFFECTIVENESS_PROVENANCE" if not mismatches else "HOLD_NATIVE_GLTF_EFFECTIVENESS_MISMATCH",
       "native_source_sha256":source["source_blend_sha256"],
       "gltf_named_morphs":names,
       "native_effective":sum(x["raw_key_effective_on_evaluated_visible_surface"] for x in src),
       "glb_effective":sum(r["actual_glb_effective"] for r in rows),
       "mismatch_indices":mismatches,"rows":rows,
       "limits":"Only actual original MPFB raw relative shape vs actual glTF target effectiveness on visible source; not pose-time expressions, anatomy or game acceptance"}
    Path(args.out).write_text(json.dumps(result,sort_keys=True,indent=2),encoding="utf-8")
    print("R051_MORPH_LINEAGE_RECEIPT "+json.dumps(result,sort_keys=True))
    if mismatches:hold("source-visible and target effectiveness differ at "+str(mismatches))
if __name__=="__main__":main()
