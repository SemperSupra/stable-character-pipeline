"""Independent W13 two-engine source SHA and indexed 3D numeric verifier."""
import hashlib,json,math,sys
from pathlib import Path
go=json.loads(Path(sys.argv[1]).read_text())
py=json.loads(Path(sys.argv[2]).read_text())
raw=Path(sys.argv[3]).read_bytes()
sha=hashlib.sha256(raw).hexdigest()
expected={"schema":"scp.ik3d.receipt.v1","source_rights":"ORIGINAL_PROGRAMMATIC_PROCEDURAL_ONLY",
          "coordinate_basis":"RIGHT_HANDED_XYZ_Y_UP_UNCALIBRATED",
          "algorithm":"ANALYTIC_3D_TWO_SEGMENT_POLE_SELECTED_NO_JOINT_LIMITS",
          "source_sha256":sha}
for k,v in expected.items():
    if go.get(k)!=v or py.get(k)!=v:raise ValueError("ENGINE_SOURCE_SCHEMA_RIGHTS_OR_SHA_DRIFT_"+k)
if go.get("solver")!="GO_ORIGINAL_ANALYTIC_3D" or py.get("solver")!="PYTHON_INDEPENDENT_NUMERIC_3D":
    raise ValueError("NOT_INDEPENDENT_SOLVERS")
a=go["cases"];b=py["cases"]
if len(a)!=5 or len(b)!=5:raise ValueError("CASE_COUNT")
max_residual=0.
for i,(left,right) in enumerate(zip(a,b)):
    if left["id"]!=right["id"] or left["status"]!=right["status"] or left["reached"]!=right["reached"]:
        raise ValueError("POSE_REACHABILITY_OR_ORDER_DRIFT")
    for field in ("start","knee","end","target","effective_target"):
        v,w=left[field],right[field]
        if len(v)!=3 or len(w)!=3:raise ValueError("NOT_TRUE_XYZ")
        for x,y in zip(v,w):
            if not math.isfinite(x) or not math.isfinite(y):raise ValueError("NONFINITE_RESULT")
            max_residual=max(max_residual,abs(x-y))
    for field in ("upper_residual","lower_residual","target_gap","pole_side"):
        x,y=left[field],right[field]
        if not math.isfinite(x) or not math.isfinite(y):raise ValueError("NONFINITE_SCALAR")
        max_residual=max(max_residual,abs(x-y))
if max_residual>1e-8:raise ValueError("INDEPENDENT_3D_IK_NUMERIC_DISAGREEMENT")
if a[-1]["reached"] or b[-1]["reached"]:raise ValueError("FALSE_POSITIVE_REACHABLE")
output={"schema":"scp.ik3d.independent_join.v1",
        "status":"PASS_GO_VS_PYTHON_3D_IK_NUMERICAL_PARITY",
        "source_sha256":sha,"num_cases":len(a),
        "max_indexed_abs_component_or_residual_difference":max_residual,
        "threshold":1e-8,
        "not_tested":["external Ozz parity","true skinned anatomy","native Blender","contact dynamics","human identity","target joint limits"]}
Path(sys.argv[4]).write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
print("W13_INDEPENDENT_3D_IK_PARITY_PASS",json.dumps(output,sort_keys=True))
