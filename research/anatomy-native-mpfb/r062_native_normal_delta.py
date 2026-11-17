"""R062 compare two actual Blender imported glTF receipts without tolerating drift.

A completed diagnostic can observe a RED while the product decision remains HOLD.
"""
import argparse
import copy
import json
import math
from pathlib import Path

def hold(msg):raise ValueError("R062_NATIVE_NORMAL_HOLD "+msg)

def compare(a,b):
    if any(x.get("schema")!="r061.native.blender.gltf-derived-parity.v1" for x in (a,b)):
        hold("source-native Blender receipt missing")
    if a.get("blender_version")!=b.get("blender_version"):
        hold("native Blender importer version drift")
    if a.get("input_glb_sha256")==b.get("input_glb_sha256"):
        hold("derived GLB and source GLB indistinguishable")
    x=a.get("records",[])
    y=b.get("records",[])
    if len(x)!=3 or len(y)!=3:hold("three native mesh records required")
    drifts=[]
    for i,(first,second) in enumerate(zip(x,y)):
        forbidden={"face_component_sha256","face_position_uv_normal_skin_weight_oriented_sha256",
                   "diagnostic_corner_normals"}
        for k in set(first)|set(second):
            if k in forbidden:continue
            if first.get(k)!=second.get(k):
                hold("non-normal native semantic mismatched node="+str(i)+" key="+k)
        if first.get("face_component_sha256",{}).get("position_uv") != second.get("face_component_sha256",{}).get("position_uv"):
            hold("per-face UV/position changed")
        if first.get("face_component_sha256",{}).get("position_uv_weights") != second.get("face_component_sha256",{}).get("position_uv_weights"):
            hold("per-face position/UV/weights changed")
        original=first.get("diagnostic_corner_normals",[])
        derived=second.get("diagnostic_corner_normals",[])
        if i==2:
            if first.get("face_component_sha256")!=second.get("face_component_sha256") or first.get("face_position_uv_normal_skin_weight_oriented_sha256") != second.get("face_position_uv_normal_skin_weight_oriented_sha256"):
                hold("human external body normal drift")
            continue
        if len(original)!=196 or len(derived)!=196:hold("expected 196 synthetic proxy faces")
        if [r["face_key_sha256"] for r in original] != [r["face_key_sha256"] for r in derived]:
            hold("face identity/key changed across imports")
        distances=[]
        for left,right in zip(original,derived):
            for l,r in zip(left["corner_normals"],right["corner_normals"]):
                if len(l)!=3 or len(r)!=3 or not all(math.isfinite(z) for z in l+r):
                    hold("nonfinite or invalid native corner normal")
                distances.append(math.sqrt(sum((l[k]-r[k])**2 for k in range(3))))
        if len(distances)!=588:hold("missing corner samples")
        distances.sort()
        nonzero=sum(d>0 for d in distances)
        if (nonzero==0)!=(first["face_position_uv_normal_skin_weight_oriented_sha256"]==second["face_position_uv_normal_skin_weight_oriented_sha256"]):
            hold("face digest inconsistent with quantified normals")
        drifts.append({
            "name":first["node"],"faces":196,"corners":588,
            "different_native_corner_normals":nonzero,
            "max_vector_delta":distances[-1],
            "p95_vector_delta":distances[int((len(distances)-1)*.95)],
            "mean_vector_delta":sum(distances)/len(distances),
            "normal_sha_original":first["face_component_sha256"]["normal_only"],
            "normal_sha_derived":second["face_component_sha256"]["normal_only"],
            "position_uv_sha":first["face_component_sha256"]["position_uv"]
        })
    if len(drifts)!=2:hold("missing two proxy mesh records")
    observed=sum(x["different_native_corner_normals"] for x in drifts)
    return {
        "schema":"r062.original-synthetic-native-normal-forensics.v1",
        "status":"FAIL_NARROW_NATIVE_CORNER_NORMAL_STRICT_EQUALITY" if observed else "PASS_NARROW_NATIVE_CORNER_NORMAL_STRICT_EQUALITY",
        "narrow_source_and_pose_attributes_equal":True,
        "native_normal_exact_equality":observed==0,
        "blender_version":a["blender_version"],
        "records":drifts,
        "limits":"A verified RED is not a numeric tolerance waiver. No rendered pixel or H.264, production model, donor organ or owner acceptance evidence."
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original",required=True)
    p.add_argument("--derived",required=True)
    p.add_argument("--out",required=True)
    z=p.parse_args()
    a=json.loads(Path(z.original).read_text())
    b=json.loads(Path(z.derived).read_text())
    r=compare(a,b)
    altered=copy.deepcopy(b)
    altered["records"][0]["face_component_sha256"]["position_uv"]="0"*64
    try: compare(a,altered)
    except ValueError as e:
        if "R062_NATIVE_NORMAL_HOLD" not in str(e):raise
    else:hold("adversarial position/UV tamper not rejected")
    r["negative_control"]={"position_uv_mutation_rejected":True}
    Path(z.out).write_text(json.dumps(r,sort_keys=True)+"\n")
    print("R062_NATIVE_NORMAL_DIAGNOSTIC "+json.dumps(r,sort_keys=True))

if __name__=="__main__":main()
