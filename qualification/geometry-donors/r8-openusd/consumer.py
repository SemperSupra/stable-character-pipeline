"""Original public-safe clean-consumer OpenUSD mesh semantics and roundtrip test."""
import hashlib
import json
import math
from pathlib import Path
import sys
from pxr import Usd,UsdGeom,Gf,Sdf

PHASE,PATH,RECEIPT=sys.argv[1:4]
path=Path(PATH)
expected_points=[(-1.0,0.0,0.0),(1.0,0.0,0.0),(1.0,2.0,0.0),(-1.0,2.0,0.0)]
counts=[3,3]
indices=[0,1,2,0,2,3]

if PHASE=="create":
    stage=Usd.Stage.CreateNew(str(path))
    if not stage:raise RuntimeError("CREATE_STAGE_FAILED")
    UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage,1.0)
    xform=UsdGeom.Xform.Define(stage,"/Scene")
    stage.SetDefaultPrim(xform.GetPrim())
    mesh=UsdGeom.Mesh.Define(stage,"/Scene/Mesh")
    mesh.CreatePointsAttr().Set([Gf.Vec3f(*p) for p in expected_points])
    mesh.CreateFaceVertexCountsAttr().Set(counts)
    mesh.CreateFaceVertexIndicesAttr().Set(indices)
    mesh.CreateSubdivisionSchemeAttr().Set(UsdGeom.Tokens.none)
    mesh.CreateDoubleSidedAttr().Set(False)
    mesh.GetPrim().CreateAttribute("pipeline:semantic",Sdf.ValueTypeNames.String).Set("original-procedural-test")
    mesh.GetPrim().SetCustomDataByKey("researchFixture", "r8-openusd")
    stage.GetRootLayer().Save()
    stage=None
elif PHASE!="verify":raise RuntimeError("UNSUPPORTED_PHASE")

stage=Usd.Stage.Open(str(path))
if not stage:raise RuntimeError("OPEN_STAGE_FAILED")
mesh=UsdGeom.Mesh.Get(stage,"/Scene/Mesh")
if not mesh or not mesh.GetPrim().IsValid():raise RuntimeError("MISSING_MESH")
pts=[tuple(float(v) for v in p) for p in mesh.GetPointsAttr().Get()]
actual_counts=list(mesh.GetFaceVertexCountsAttr().Get())
actual_indices=list(mesh.GetFaceVertexIndicesAttr().Get())
semantic=mesh.GetPrim().GetAttribute("pipeline:semantic").Get()
custom=mesh.GetPrim().GetCustomDataByKey("researchFixture")
up_axis=str(UsdGeom.GetStageUpAxis(stage))
meters=float(UsdGeom.GetStageMetersPerUnit(stage))
expected=(pts==expected_points and actual_counts==counts and actual_indices==indices and
  semantic=="original-procedural-test" and custom=="r8-openusd" and up_axis=="Z" and meters==1.0)
result={"schema":"openusd-stage-native-consumer/v1","phase":PHASE,
        "status":"PASS" if expected else "FAIL","usd_version":Usd.GetVersion(),
        "stage_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
        "points":pts,"counts":actual_counts,"indices":actual_indices,
        "semantic":semantic,"custom":custom,"up_axis":up_axis,"meters_per_unit":meters}
Path(RECEIPT).write_text(json.dumps(result,indent=2,sort_keys=True,default=str)+"\n")
print(json.dumps(result,sort_keys=True,default=str))
if not expected:raise RuntimeError("USD_ROUNDTRIP_SEMANTIC_FAILURE")
