"""Cross-version material admission contract, independent from Blender runtime."""
import json
import math
from pathlib import Path

EXPECTED = {
    "SyntheticMovingSkin": {"material":"OriginalSyntheticSurface", "color":[0.62,0.24,0.12,1.0], "roughness":0.58},
    "SyntheticFloor": {"material":"GreyFloor", "color":[0.44,0.44,0.44,1.0], "roughness":0.58}
}
VERSIONS=("4.5.16","5.2.4","5.3.0")

def validate_manifest(data, version):
    if not isinstance(data,dict) or data.get("schema")!="scp.r095.materials.v1" or data.get("version")!=version:
        raise ValueError("manifest schema/version mismatch")
    if data.get("render")!="CYCLES_CPU_8SPP" or data.get("view_transform")!="Standard":
        raise ValueError("render configuration mismatch")
    if set(data.get("objects",{}))!=set(EXPECTED):
        raise ValueError("material objects missing or unexpected")
    for name, reference in EXPECTED.items():
        obj=data["objects"][name]
        if obj.get("material")!=reference["material"] or obj.get("use_nodes") is not True:
            raise ValueError("unqualified material or no nodes: "+name)
        if obj.get("shader")!="ShaderNodeBsdfPrincipled" or obj.get("surface_connected") is not True:
            raise ValueError("shader fallback/disconnected: "+name)
        color=obj.get("color")
        rough=obj.get("roughness")
        if not isinstance(color,list) or len(color)!=4 or any(not isinstance(x,(int,float)) or isinstance(x,bool) or not math.isfinite(x) for x in color):
            raise ValueError("invalid base color: "+name)
        if not isinstance(rough,(int,float)) or isinstance(rough,bool) or not math.isfinite(rough):
            raise ValueError("invalid roughness: "+name)
        if any(abs(a-b)>1e-6 for a,b in zip(color,reference["color"])) or abs(rough-reference["roughness"])>1e-6:
            raise ValueError("material semantic drift: "+name)
    return True

def validate_files(root):
    for version in VERSIONS:
        path=Path(root)/("r095-"+version)/"material_manifest.json"
        validate_manifest(json.loads(path.read_text(encoding="utf-8")),version)
    return True
