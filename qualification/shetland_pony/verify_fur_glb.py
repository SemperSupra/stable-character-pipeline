"""Read actual exported GLB and exact source-level fur density receipt."""
import json,struct,sys
from pathlib import Path
def verify(glb,receipt):
    data=Path(glb).read_bytes()
    if data[:4]!=b"glTF" or struct.unpack_from("<I",data,8)[0]!=len(data):
        raise ValueError("invalid glTF binary")
    n,kind=struct.unpack_from("<II",data,12)
    if kind!=0x4e4f534a:raise ValueError("GLB JSON missing")
    gltf=json.loads(data[20:20+n].decode().strip())
    source=json.loads(Path(receipt).read_text())
    if source["schema"]!="equine.fur.skinned.v1" or source["total_strands"]<9000:
        raise ValueError("not enough authored fiber geometry")
    fur=[m for m in gltf.get("meshes",[]) if m.get("name","").startswith("fur_geometry_")]
    if len(fur)<10:raise ValueError("fiber mesh missing in exported GLB")
    for mesh in fur:
        for primitive in mesh["primitives"]:
            attributes=primitive.get("attributes",{})
            if not ("JOINTS_0" in attributes and "WEIGHTS_0" in attributes):
                raise ValueError("fur not attached to skeletal animation")
    torso=[m for m in fur if "continuous_shetland_barrel" in m.get("name","")]
    if len(torso)!=1:raise ValueError("torso fiber mesh missing")
    return {"schema":"equine.fur.native.v1","verdict":"ACTUAL_SKINNED_FIBER_GEOMETRY_IN_GLTF",
      "total_strands":source["total_strands"],"fur_meshes":len(fur),
      "source_actor_fur_groups":len(source["sources"]),
      "export_skin_count":len(gltf.get("skins",[])),
      "animation_count":len(gltf.get("animations",[])),
      "photorealism":"NOT_ACCEPTED","groom_quality":"NOT_ACCEPTED"}
if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("source GLB receipt.json")
    print(json.dumps(verify(*sys.argv[1:]),sort_keys=True))
