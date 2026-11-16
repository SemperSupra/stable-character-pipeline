"""R054 glTF bufferView SHA-only lineage; original-synthetic source-safe.

Fingerprints each declared glTF binary slice and reports machine-decidable
accessor/animation/image references. Never emits any vertex, animation or image
bytes. A changed hash is a localization clue, NOT a claim of changed motion.
"""
import argparse
import hashlib
import json
from pathlib import Path
from gltf_godot_morph_compare import parse_glb

def fail(msg):
    raise ValueError("R054_GLTF_VIEW_HOLD "+msg)

def roles_for(g):
    refs={}
    def use(view,role):
        if not isinstance(view,int) or view<0 or view>=len(g.get("bufferViews",[])):
            fail("out of range bufferView reference")
        refs.setdefault(view,set()).add(role)
    def acc(index,role):
        access=g.get("accessors",[])
        if not isinstance(index,int) or index<0 or index>=len(access):
            fail("out of range accessor reference")
        a=access[index]
        if "bufferView" in a:use(a["bufferView"],role)
        sp=a.get("sparse")
        if sp:
            use(sp["indices"]["bufferView"],role+":sparse-indices")
            use(sp["values"]["bufferView"],role+":sparse-values")
    for mi,mesh in enumerate(g.get("meshes",[])):
        for pi,primitive in enumerate(mesh.get("primitives",[])):
            base="mesh:"+str(mi)+":prim:"+str(pi)
            for key,val in primitive.get("attributes",{}).items():
                acc(val,base+":attribute:"+key)
            if "indices" in primitive:acc(primitive["indices"],base+":indices")
            for ti,target in enumerate(primitive.get("targets",[])):
                for key,val in target.items():
                    acc(val,base+":target:"+str(ti)+":"+key)
    for si,skin in enumerate(g.get("skins",[])):
        if "inverseBindMatrices" in skin:
            acc(skin["inverseBindMatrices"],"skin:"+str(si)+":inverseBindMatrices")
    for ai,anim in enumerate(g.get("animations",[])):
        for si,sampler in enumerate(anim.get("samplers",[])):
            acc(sampler["input"],"animation:"+str(ai)+":sampler:"+str(si)+":time")
            acc(sampler["output"],"animation:"+str(ai)+":sampler:"+str(si)+":output")
    for ii,img in enumerate(g.get("images",[])):
        if "bufferView" in img:use(img["bufferView"],"image:"+str(ii))
    return refs

def audit(path):
    g,payload=parse_glb(path)
    views=g.get("bufferViews",[])
    if not views or len(views)>50000:fail("invalid number of glTF bufferViews")
    users=roles_for(g)
    rows=[]
    for index,v in enumerate(views):
        start=v.get("byteOffset",0)
        size=v.get("byteLength")
        if not isinstance(start,int) or not isinstance(size,int):
            fail("noninteger bufferView span")
        if start<0 or size<=0 or start+size>len(payload):
            fail("invalid bounded bufferView span")
        roles=sorted(users.get(index,()))
        data=payload[start:start+size]
        rows.append({
          "index":index,
          "start":start,
          "bytes":size,
          "sha256":hashlib.sha256(data).hexdigest(),
          "role_count":len(roles),
          "roles":roles[:16],
          "roles_truncated":len(roles)>16,
        })
    return {"schema":"r054.gltf.bufferview-lineage.v1",
      "status":"PASS_NARROW_BOUNDARY_HASHES",
      "buffer_views":len(rows),
      "buffer_bytes":len(payload),
      "unreferenced_views":sum(row["role_count"]==0 for row in rows),
      "views":rows,
      "limits":"A role describes glTF index reference, not semantic equivalence or visible effects. No binary source publication, full runtime parity, model acceptance or certified reproducibility"},g,payload

def negative(g,payload,rows):
    # Flip one byte of the first referenced non-empty buffer view in memory;
    # verify exact view hash changes without modifying its original GLB.
    candidate=next((r for r in rows if r["role_count"]>0 and r["bytes"]>32),None)
    if not candidate:fail("no testable referenced view")
    start=candidate["start"]
    changed=bytearray(payload)
    changed[start+16]^=1
    alternate=hashlib.sha256(memoryview(changed)[start:start+candidate["bytes"]]).hexdigest()
    if alternate==candidate["sha256"]:fail("deliberate binary mutation missed")
    return {"mutated_view_index":candidate["index"],
            "mutation_detected":True,
            "source_original_unchanged":True}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--glb",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--negative",action="store_true")
    a=p.parse_args()
    record,g,bin=audit(a.glb)
    if a.negative:record["adversarial_control"]=negative(g,bin,record["views"])
    Path(a.out).write_text(json.dumps(record,sort_keys=True)+"\n",encoding="utf-8")
    print("R054_BUFFER_VIEW_ATTESTATION "+json.dumps(record,sort_keys=True))
if __name__=="__main__":main()
