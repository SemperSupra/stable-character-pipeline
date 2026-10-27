#!/usr/bin/env python3
"""G9: rights-clean original PMX vertex morphs + VMD face tracks.

Only synthetic four-by-four test mesh, not a human face or identity.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

def module(root, name):
    path=root/"mmd_tools"/"core"/name/"__init__.py"
    spec=importlib.util.spec_from_file_location("scp_morph_"+name,path)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

def main():
    p=argparse.ArgumentParser()
    for n in ("source","out"):
        p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    pmx=module(a.source,"pmx")
    vmd=module(a.source,"vmd")
    model=pmx.Model()
    model.name="表情試験"
    model.name_e="SCP original synthetic face-morph grid"
    model.comment="Synthetic grid, not a real face, identity, styling or scan"
    bone=pmx.Bone()
    bone.name,bone.name_e="センター","Center"
    bone.location=(0.0,0.0,0.0)
    bone.displayConnection=(0.0,1.0,0.0)
    model.bones=[bone]
    # Authored 4x4 test grid, two vertex targets with disjoint offsets.
    levels=(-1.5,-0.5,0.5,1.5)
    for j,y in enumerate(levels):
        for i,x in enumerate(levels):
            vertex=pmx.Vertex()
            vertex.co=(x,y,0.0)
            vertex.normal=(0.0,0.0,1.0)
            vertex.uv=(i/3.0,j/3.0)
            weight=pmx.BoneWeight()
            weight.type=pmx.BoneWeight.BDEF1
            weight.bones=[0]
            vertex.weight=weight
            model.vertices.append(vertex)
    for j in range(3):
        for i in range(3):
            n=j*4+i
            model.faces.extend(((n,n+1,n+5),(n,n+5,n+4)))
    mat=pmx.Material()
    mat.name,mat.name_e="原作の形状","SCP original synthetic grid"
    mat.diffuse=(0.42,0.62,0.86,1.0)
    mat.ambient=(0.1,0.1,0.1)
    mat.specular=(0.0,0.0,0.0)
    mat.edge_color=(0.0,0.0,0.0,1.0)
    mat.vertex_count=len(model.faces)*3
    model.materials=[mat]
    morph_specs=[
      ("まばたき","Blink",pmx.Morph.CATEGORY_EYE,{8:(0.0,-.45,0.0),9:(0.0,-.65,0.0),10:(0.0,-.65,0.0),11:(0.0,-.45,0.0)}),
      ("笑い","Smile",pmx.Morph.CATEGORY_MOUTH,{0:(0.0,.55,0.0),1:(0.0,.14,0.0),2:(0.0,.14,0.0),3:(0.0,.55,0.0)})
    ]
    for name,english,kind,offs in morph_specs:
        morph=pmx.VertexMorph(name,english,kind)
        for index,delta in offs.items():
            off=pmx.VertexMorphOffset()
            off.index=index
            off.offset=delta
            morph.offsets.append(off)
        model.morphs.append(morph)
    model_path=a.out/"synthetic_face_grid.pmx"
    pmx.save(str(model_path),model)
    loaded=pmx.load(str(model_path))
    assert len(loaded.vertices)==16 and len(loaded.faces)==18
    assert len(loaded.morphs)==2 and [m.name for m in loaded.morphs]==["まばたき","笑い"]
    assert all(len(m.offsets)==4 and isinstance(m,pmx.VertexMorph) for m in loaded.morphs)
    animation=vmd.File()
    animation.header=vmd.Header()
    animation.header.model_name=model.name
    animation.shapeKeyAnimation=vmd.ShapeKeyAnimation()
    specs=[("まばたき",[(0,0.0),(15,1.0),(30,0.0)]),
           ("笑い",[(0,0.0),(15,0.35),(30,1.0)])]
    for name,sequence in specs:
        for frame,weight in sequence:
            key=vmd.ShapeKeyFrameKey()
            key.frame_number=frame
            key.weight=weight
            animation.shapeKeyAnimation[name].append(key)
    motion=a.out/"synthetic_face_motion.vmd"
    animation.save(filepath=str(motion))
    parsed=vmd.File()
    parsed.load(filepath=str(motion))
    assert set(parsed.shapeKeyAnimation)=={"まばたき","笑い"}
    for name,sequence in specs:
        observed=parsed.shapeKeyAnimation[name]
        assert [k.frame_number for k in observed]==[x[0] for x in sequence]
        assert all(abs(k.weight-w)<1e-6 for k,(_,w) in zip(observed,sequence))
    repeat=a.out/"repeat.vmd"
    animation.save(filepath=str(repeat))
    assert repeat.read_bytes()==motion.read_bytes()
    repeat.unlink()
    out={
      "schema":"scp.mmd.morph.fixture.v1",
      "status":"PASS_ORIGINAL_PMX_TWO_VERTEX_MORPHS_AND_VMD_KEYFRAME_ROUNDTRIP",
      "model":"original grid, not human identity or photorealistic face",
      "source_vertices":16,
      "source_triangles":18,
      "morphs":{name:{"offset_count":len(offs),"keyframes":values} for (name,_,_,offs),(_,values) in zip(morph_specs,specs)},
      "sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (model_path,motion)},
      "rights":"self-authored MMD test files; no community assets"
    }
    (a.out/"fixture_receipt.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))

if __name__=="__main__":
    main()
