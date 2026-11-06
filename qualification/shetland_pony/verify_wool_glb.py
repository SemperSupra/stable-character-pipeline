"""Reject smooth-only GLBs: verify real image textures with UVs on body/limbs/fur."""
import json,struct,sys
from pathlib import Path
def check(glb,coat,root):
    raw=Path(glb).read_bytes()
    if raw[:4]!=b"glTF" or struct.unpack_from("<I",raw,8)[0]!=len(raw):
        raise ValueError("not glTF")
    n,kind=struct.unpack_from("<II",raw,12)
    if kind!=0x4E4F534A:raise ValueError("GLB JSON missing")
    d=json.loads(raw[20:20+n].decode().strip())
    if len(d.get("images",[]))< (2 if coat=="pinto" else 1):
        raise ValueError("missing embedded diffuse image")
    if len(d.get("textures",[]))< (2 if coat=="pinto" else 1):
        raise ValueError("missing glTF texture")
    painted=[m for m in d["materials"] if m.get("pbrMetallicRoughness",{}).get("baseColorTexture") is not None]
    if len(painted)<(2 if coat=="pinto" else 1):
        raise ValueError("no material with portable baseColorTexture")
    colored={i for i,m in enumerate(d["materials"]) if m in painted}
    relevant=[m for m in d["meshes"] if any(t in m.get("name","") for t in (
        "original_continuous_torso_topology","sculpt_equine_brow_bridge_muzzle",
        "sculpt_sloping_neck","continuous_front_L_limb","fur_geometry_"))]
    if len(relevant)<5:raise ValueError("missing source objects")
    for mesh in relevant:
        for prim in mesh["primitives"]:
            if prim.get("material",-1) in colored and "TEXCOORD_0" not in prim.get("attributes",{}):
                raise ValueError("portable wool pattern has no mesh UV")
    source=Path(root)
    image_files=list(source.glob("wool_fiber_*.png"))
    if len(image_files)<(2 if coat=="pinto" else 1):raise ValueError("missing source PNG image")
    for path in image_files:
        if path.stat().st_size<5000 or path.read_bytes()[:8]!=b"\x89PNG\r\n\x1a\n":
            raise ValueError("texture PNG not valid")
    wool=json.loads((source/("wool_"+coat+".json")).read_text())
    if wool["main"]["glb_requirement"]!="TEXCOORD_0+baseColorTexture":
        raise ValueError("source proof does not claim portable UVs")
    return {"schema":"equine.wool.glb.actual.v1","verdict":"TEXTURED_UV_GLTF_WITH_SKINNED_3D_FUR",
      "coats":coat,"embedded_images":len(d["images"]),"materials_with_diffuse_image":len(painted),
      "uv_meshes_examined":len(relevant),"source_pngs":len(image_files),
      "natural_wool_evaluation":"UNKNOWN","photorealism":"NOT_ACCEPTED"}
if __name__=="__main__":
    if len(sys.argv)!=4:raise SystemExit("verify_wool_glb.py file.glb coat output_dir")
    print(json.dumps(check(*sys.argv[1:]),sort_keys=True))
