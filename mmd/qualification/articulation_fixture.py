#!/usr/bin/env python3
"""Original articulated MMD PMX/VMD fixture; no third-party human or dance data."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

def module(root, name):
    f = root / "mmd_tools" / "core" / name / "__init__.py"
    spec = importlib.util.spec_from_file_location("scp_articulation_" + name, f)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",required=True,type=Path)
    ap.add_argument("--out",required=True,type=Path)
    a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    pmx=module(a.source,"pmx")
    vmd=module(a.source,"vmd")
    model=pmx.Model()
    model.name="関節試験"
    model.name_e="SCP original 3-bone articulated ribbon"
    model.comment="Original geometric CPU rig test, not a human scan or external character"
    labels=["センター","左腕","左手首"]
    for idx,(label,y) in enumerate(zip(labels,(0.0,1.0,2.0))):
        b=pmx.Bone()
        b.name=label
        b.name_e=("Center","Arm","Wrist")[idx]
        b.location=(0.0,y,0.0)
        b.parent=(idx-1 if idx else None)
        b.displayConnection=(0.0,0.5,0.0)
        model.bones.append(b)
    # Eight vertices form one continuous 3-segment vertical ribbon;
    # elbow/wrist rows have intentionally mixed weights to exercise BDEF2.
    rows=[0.0,1.0,2.0,3.0]
    weight_cases=[(0,None,1.0),(0,1,.45),(1,2,.65),(2,None,1.0)]
    for row,(bone0,bone1,ratio) in enumerate(weight_cases):
        y=rows[row]
        for x,u in ((-0.16,0.0),(0.16,1.0)):
            v=pmx.Vertex()
            v.co=(x,y,0.0)
            v.normal=(0.0,0.0,1.0)
            v.uv=(u,y/3.0)
            w=pmx.BoneWeight()
            if bone1 is None:
                w.type=pmx.BoneWeight.BDEF1
                w.bones=[bone0]
            else:
                w.type=pmx.BoneWeight.BDEF2
                w.bones=[bone0,bone1]
                w.weights=[ratio]
            v.weight=w
            model.vertices.append(v)
    for i in range(3):
        k=i*2
        model.faces.extend(((k,k+1,k+3),(k,k+3,k+2)))
    mat=pmx.Material()
    mat.name="合成"
    mat.name_e="Synthetic diagnostic geometry"
    mat.diffuse=(0.1,0.5,0.9,1.0)
    mat.specular=(0.0,0.0,0.0)
    mat.ambient=(0.15,0.15,0.15)
    mat.edge_color=(0.0,0.0,0.0,1.0)
    mat.vertex_count=len(model.faces)*3
    model.materials=[mat]
    pmxfile=a.out/"articulated_ribbon.pmx"
    pmx.save(str(pmxfile),model)
    m2=pmx.load(str(pmxfile))
    assert len(m2.vertices)==8 and len(m2.faces)==6 and len(m2.bones)==3
    assert [b.name for b in m2.bones]==labels
    assert sorted(set(v.weight.type for v in m2.vertices)) == [0,1]
    assert all(m2.vertices[i].weight.type==1 for i in (2,3,4,5))
    anim=vmd.File()
    anim.header=vmd.Header()
    anim.header.model_name=model.name
    anim.boneAnimation=vmd.BoneAnimation()
    for name,axis,angle in (
      ("左腕","z",math.radians(48)),
      ("左手首","x",math.radians(-37)),
    ):
        for frame in (0,30):
            k=vmd.BoneFrameKey()
            k.frame_number=frame
            k.location=(0.0,0.0,0.0)
            amt=angle if frame else 0
            sine=math.sin(amt/2.0)
            k.rotation=(0.0,0.0,sine,math.cos(amt/2.0)) if axis=="z" else (sine,0.0,0.0,math.cos(amt/2.0))
            k.interp=(20,20,107,107)*16
            anim.boneAnimation[name].append(k)
    motion=a.out/"articulated_ribbon.vmd"
    anim.save(filepath=str(motion))
    parsed=vmd.File()
    parsed.load(filepath=str(motion))
    assert set(parsed.boneAnimation)=={"左腕","左手首"}
    assert all([x.frame_number for x in parsed.boneAnimation[n]]==[0,30] for n in parsed.boneAnimation)
    repeat=a.out/"repeat.vmd"
    anim.save(filepath=str(repeat))
    assert repeat.read_bytes()==motion.read_bytes()
    repeat.unlink()
    receipt={
      "schema":"scp.mmd.articulation.fixture.v1",
      "result":"PASS_THREE_BONE_BDEF2_AND_TWO_ROTATION_TRACKS",
      "source":"original Python fixture, real pinned upstream PMX/VMD file serializers",
      "rig_labels":labels,
      "vertices":len(m2.vertices),
      "triangles":len(m2.faces),
      "bone_weights":{"BDEF1":4,"BDEF2":4},
      "rotation_tracks":["左腕","左手首"],
      "frames":[0,30],
      "sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (pmxfile,motion)},
      "rights":"original geometry and synthetic keyframes; no external motion or human character assets"
    }
    (a.out/"fixture_receipt.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print(json.dumps(receipt,sort_keys=True))
if __name__=="__main__":
    main()
