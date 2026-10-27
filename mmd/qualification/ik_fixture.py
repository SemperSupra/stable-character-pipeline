#!/usr/bin/env python3
"""G10a original bounded two-link MMD IK leg fixture (not a native solver proof)."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

def module(root,name):
    p=root/"mmd_tools"/"core"/name/"__init__.py"
    spec=importlib.util.spec_from_file_location("scp_ik_"+name,p)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    pmx=module(a.source,"pmx")
    vmd=module(a.source,"vmd")
    m=pmx.Model()
    m.name="接地試験"
    m.name_e="SCP self-authored two-link IK structural qualification"
    m.comment="Fictitious mechanical leg and IK goal, not a character scan"
    specs=[
      ("腰","Hip",(0.0,2.0,0.0),None),
      ("ひざ","Knee",(0.25,1.0,0.0),0),
      ("足首","Ankle",(0.0,0.0,0.0),1),
      ("足ＩＫ","Foot IK",(0.0,0.0,0.0),None)
    ]
    for name,en,point,parent in specs:
        bone=pmx.Bone()
        bone.name,bone.name_e=name,en
        bone.location=point
        bone.parent=parent
        bone.displayConnection=(0.0,.5,0.0)
        m.bones.append(bone)
    ctrl=m.bones[3]
    ctrl.isIK=True
    ctrl.target=2
    ctrl.loopCount=24
    ctrl.rotationConstraint=.45
    for target in (1,0):
        link=pmx.IKLink()
        link.target=target
        ctrl.ik_links.append(link)
    for row,y in enumerate((0.0,1.0,2.0)):
        for x,u in ((-.16,0.0),(.16,1.0)):
            v=pmx.Vertex()
            v.co=(x,y,0.0)
            v.normal=(0.0,0.0,1.0)
            v.uv=(u,y/2.0)
            w=pmx.BoneWeight()
            w.type=pmx.BoneWeight.BDEF1
            w.bones=[(2,1,0)[row]]
            v.weight=w
            m.vertices.append(v)
    for row in (0,1):
        q=row*2
        m.faces.extend(((q,q+1,q+3),(q,q+3,q+2)))
    mat=pmx.Material()
    mat.name,mat.name_e="合成脚","Original synthetic leg"
    mat.diffuse=(.35,.55,.85,1)
    mat.ambient=(.1,.1,.1)
    mat.specular=(0,0,0)
    mat.edge_color=(0,0,0,1)
    mat.vertex_count=len(m.faces)*3
    m.materials=[mat]
    model=a.out/"synthetic_two_link_ik.pmx"
    pmx.save(str(model),m)
    loaded=pmx.load(str(model))
    assert len(loaded.bones)==4 and len(loaded.vertices)==6 and len(loaded.faces)==4
    assert loaded.bones[3].isIK and loaded.bones[3].target==2
    assert [link.target for link in loaded.bones[3].ik_links]==[1,0]
    assert loaded.bones[3].loopCount==24
    anim=vmd.File()
    anim.header=vmd.Header()
    anim.header.model_name=m.name
    anim.boneAnimation=vmd.BoneAnimation()
    for frame,location in ((0,(0.0,0.0,0.0)),(30,(.35,.2,0.0))):
        key=vmd.BoneFrameKey()
        key.frame_number=frame
        key.location=location
        key.rotation=(0.0,0.0,0.0,1.0)
        key.interp=(20,20,107,107)*16
        anim.boneAnimation["足ＩＫ"].append(key)
    motion=a.out/"synthetic_foot_goal.vmd"
    anim.save(filepath=str(motion))
    check=vmd.File()
    check.load(filepath=str(motion))
    assert len(check.boneAnimation["足ＩＫ"])==2
    assert abs(check.boneAnimation["足ＩＫ"][-1].location[0]-.35)<1e-5
    receipt={
      "schema":"scp.mmd.ik.fixture.v1",
      "status":"PASS_ORIGINAL_TWO_LINK_IK_PMX_AND_SOURCE_VMD",
      "bone_names":[row[0] for row in specs],
      "source_ik":{"control":3,"end_effector":2,"links":[1,0],"iterations":24},
      "source_ground_plane_y":0.0,
      "source_goal_frames":[0,30],
      "rights":"synthetic self-authored IK rig, no third-party dancers or scans",
      "hashes":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (model,motion)}
    }
    (a.out/"ik_fixture_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
if __name__=="__main__":
    main()
