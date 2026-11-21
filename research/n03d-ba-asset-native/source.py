"""N03D-BA: strictly pinned upstream assets and standalone independent GLB structure oracle.

Every asset claim is a research observation, not a license or gait promotion.
No source bits embedded in artifacts; bytes remain ephemeral to public runner.
"""
import argparse,hashlib,json,math,struct
from pathlib import Path
from urllib.request import Request,urlopen

SCHEMA="scp.n03d-ba.asset-audit.v1"
def need(ok,msg):
    if not ok:raise ValueError(msg)
def candidates(path):
    d=json.loads(Path(path).read_text())
    need(d.get("schema")=="scp.n03d-ba.source-asset-registry.v1","REGISTRY_AUTHORITY")
    a=d.get("candidates",[])
    need(len(a)==4 and len({x.get("id") for x in a})==4,"CANDIDATE_COUNT")
    for x in a:
        need(len(x["commit"])==40 and len(x["model_blob"])==40 and
             x.get("production_admitted") is False and
             x.get("public_research_only") is True,
             "SOURCE_RIGHTS_OR_COMMIT")
    return {x["id"]:x for x in a}
def blobsha(data):
    return hashlib.sha1(("blob "+str(len(data))+"\0").encode()+data).hexdigest()
def asset(data,expected_blob,name):
    need(blobsha(data)==expected_blob,"UPSTREAM_GIT_BLOB_MISMATCH_"+name)
    return {"source_git_blob_sha1":expected_blob,"sha256":hashlib.sha256(data).hexdigest(),
            "bytes":len(data),"exact_verified":True}
def acquire(source,dest):
    dest=Path(dest);dest.mkdir(parents=True,exist_ok=True)
    out={}
    for k in ("model","motion"):
        if k not in source:continue
        path=source[k]
        url="https://raw.githubusercontent.com/"+source["repo"]+"/"+source["commit"]+"/"+path
        data=urlopen(Request(url,headers={"User-Agent":"SCP-source-admission/1.0"}),timeout=90).read()
        out[k]=asset(data,source[k+"_blob"],k)
        (dest/Path(path).name).write_bytes(data)
    return out
def glb(data):
    need(len(data)>=20 and data[:4]==b"glTF","GLB_MAGIC")
    version,total=struct.unpack_from("<II",data,4)
    need(version==2 and total==len(data),"GLB_VERSION_LENGTH")
    length,kind=struct.unpack_from("<I4s",data,12)
    need(kind==b"JSON" and length>2 and 20+length<=len(data),"GLB_JSON_CHUNK")
    x=json.loads(data[20:20+length].decode("utf-8"))
    skins=x.get("skins",[])
    nodes=x.get("nodes",[])
    actions=x.get("animations",[])
    need(isinstance(skins,list) and isinstance(nodes,list) and isinstance(actions,list),"GLB_ROOT_TYPES")
    skinned=[(i,n) for i,n in enumerate(nodes) if "skin" in n and "mesh" in n]
    for i,n in skinned:
        need(isinstance(n["skin"],int) and 0<=n["skin"]<len(skins),"SKIN_REFERENCE")
    joints=sum(len(s.get("joints",[])) for s in skins)
    need(joints>0 and len(skinned)>0,"NO_SKIN")
    names=[a.get("name",f"clip-{i}") for i,a in enumerate(actions)]
    channels=sum(len(a.get("channels",[])) for a in actions)
    paths=sorted(set(ch.get("target",{}).get("path","unknown") for a in actions for ch in a.get("channels",[])))
    return {"mesh_nodes_with_skin":len(skinned),"skins":len(skins),
            "joint_references":joints,
            "animation_count":len(actions),"animation_names":names[:30],
            "animation_channels":channels,"animated_paths":paths,
            "source_gltf_version":version,"rig_skin_structurally_present":True,
            "animation_structurally_present":len(actions)>0 and channels>0}
def blend(data):
    need(len(data)>12 and data[:7]==b"BLENDER","BLEND_MAGIC")
    return {"blender_header":data[:12].decode("latin-1"),
            "blender_binary_structurally_present":True,
            "motion_in_blend_unverified_by_header":True}
def dae(data):
    import xml.etree.ElementTree as ET
    root=ET.fromstring(data)
    ns="{http://www.collada.org/2005/11/COLLADASchema}"
    return {"collada_root":root.tag.rsplit("}",1)[-1],"animation_count":len(root.findall(".//"+ns+"library_animations/"+ns+"animation")),
            "controller_count":len(root.findall(".//"+ns+"library_controllers/"+ns+"controller"))}
def report(s,receipts,files):
    a=Path(files[s["model"]]).read_bytes()
    info=glb(a) if s["expected_format"]=="GLB" else blend(a)
    if s.get("motion"):
        info["external_motion_collada"]=dae(Path(files[s["motion"]]).read_bytes())
    return {"schema":SCHEMA,"candidate":s["id"],"source_repo":s["repo"],
            "source_commit":s["commit"],"assets":receipts,
            "metadata":info,"code_license":s["code_license"],
            "model_license":s["model_license"],"motion_license":s["motion_license"],
            "source_only_original_or_public":True,
            "research_asset_in_runner_only":True,"production_admitted":False,
            "physical_contact_accepted":False,"mvp_accepted":False,
            "status":"SOURCE_BYTES_VERIFIED_STRUCTURAL_ONLY_HOLD"}
def independent(r):
    need(r.get("schema")==SCHEMA and r.get("source_only_original_or_public") is True and
         r.get("research_asset_in_runner_only") is True and
         r.get("production_admitted") is False and
         r.get("physical_contact_accepted") is False and r.get("mvp_accepted") is False and
         r.get("status")=="SOURCE_BYTES_VERIFIED_STRUCTURAL_ONLY_HOLD","FORGED_GAIT_PROMOTION")
    need(len(r["source_commit"])==40 and len(r["assets"])>=1,"SOURCE_PIN_MISSING")
    for a in r["assets"].values():
        need(a.get("exact_verified") is True and
             len(a["source_git_blob_sha1"])==40 and len(a["sha256"])==64 and
             type(a["bytes"])==int and a["bytes"]>1024,"ASSET_DIGEST_MISSING")
    return "HOLD"
def cli():
    a=argparse.ArgumentParser()
    a.add_argument("--registry",required=True);a.add_argument("--candidate",required=True)
    a.add_argument("--work",required=True);a.add_argument("--output",required=True)
    args=a.parse_args()
    s=candidates(args.registry)[args.candidate]
    receipts=acquire(s,args.work)
    files={k:str(Path(args.work)/Path(s[k]).name) for k in receipts}
    doc=report(s,receipts,files)
    assert independent(doc)=="HOLD"
    Path(args.output).write_text(json.dumps(doc,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("N03D_BA_SOURCE_AUDIT",json.dumps({"id":s["id"],"assets":receipts,"metadata":doc["metadata"],"status":"HOLD"},sort_keys=True),flush=True)
if __name__=="__main__":cli()
