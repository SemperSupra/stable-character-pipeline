"""R061 independent Blender import receipt comparator; SHA-only source-safe."""
import argparse
import copy
import json
from pathlib import Path

def hold(reason):
    raise ValueError("R061_BLENDER_IMPORT_HOLD "+reason)

def compare(a,b):
    expected="r061.native.blender.gltf-derived-parity.v1"
    if a.get("schema")!=expected or b.get("schema")!=expected or \
      a.get("status")!="PASS_NARROW_BLENDER_GLTF_IMPORT_FINGERPRINT" or \
      b.get("status")!="PASS_NARROW_BLENDER_GLTF_IMPORT_FINGERPRINT":
        hold("native import evidence schema/status invalid")
    if a.get("input_glb_sha256")==b.get("input_glb_sha256"):
        hold("candidate source GLB did not change; no actual derived test")
    if a.get("blender_version")!=b.get("blender_version"):
        hold("different native importer versions")
    if a.get("imported_meshes")!=3 or b.get("imported_meshes")!=3:
        hold("incomplete mesh import")
    x=a.get("records",[])
    y=b.get("records",[])
    if len(x)!=3 or len(y)!=3:hold("source or derived changed named mesh count")
    for i,(left,right) in enumerate(zip(x,y)):
        if left!=right:
            changed=[k for k in sorted(set(left)|set(right)) if left.get(k)!=right.get(k)]
            hold("native import semantic mismatch mesh "+str(i)+" fields="+",".join(changed[:16]))
    return {
      "schema":"r061.original-vs-derived-native-blender.v1",
      "status":"PASS_NARROW_ACTUAL_NATIVE_IMPORT_SEMANTIC_EQUALITY",
      "original_glb_sha256":a["input_glb_sha256"],
      "derived_glb_sha256":b["input_glb_sha256"],
      "blender_version":a["blender_version"],
      "matched_meshes":3,
      "native_meshes_identical_per_verified_receipt":True,
      "comparison_fields":sorted(x[0]),
      "limits":"Only source-safe native Blender glTF-import semantic digest at frames 1/12/24 and mesh/UV/normal/weights/morph; no image render, actual Godot/3D engine, anatomical fidelity, or film acceptance"
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original",required=True)
    p.add_argument("--derived",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    a=json.loads(Path(args.original).read_text(encoding="utf-8"))
    b=json.loads(Path(args.derived).read_text(encoding="utf-8"))
    receipt=compare(a,b)
    tampered=copy.deepcopy(b)
    tampered["records"][0]["face_position_uv_normal_skin_weight_oriented_sha256"]="0"*64
    try:compare(a,tampered)
    except ValueError as e:
        if "R061_BLENDER_IMPORT_HOLD" not in str(e):raise
    else:hold("deliberate native face digest tamper not rejected")
    receipt["adversarial_control"]={"changed_face_hash_rejected":True,"original_probe_unmodified":True}
    Path(args.out).write_text(json.dumps(receipt,sort_keys=True)+"\n",encoding="utf-8")
    print("R061_BLENDER_IMPORT_PARITY "+json.dumps(receipt,sort_keys=True))
if __name__=="__main__":main()
