"""Independent W13 numeric oracle against derived typed W16-A packet."""
import hashlib, json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "walk_w16b"))
from independent_ik import process
src = Path(sys.argv[1]).read_bytes()
p = json.loads(Path(sys.argv[2]).read_text())
r = json.loads(Path(sys.argv[3]).read_text())
oracle = process(src)
assert r["SourceFixtureSHA256"] == hashlib.sha256(src).hexdigest() == oracle["source_sha256"]
assert r["Status"] == "PASS_STRUCTURAL_AND_ANALYTIC_SYNTHETIC_DERIVATION_ONLY"
assert not r["NativeSourceTimeAdmitted"] and not r["ActualWeightedSkinAdmitted"] and r["SyntheticTimeOnly"]
assert p["origin_commit_sha"] == r["OriginalW13ACommit"] == "1967886686d008f8db33e5c90328928d5fe944ed"
assert r["StructuralW16ACommit"] == "0b283718183dff20313c3ba4517830245267c053"
assert p["schema"] == "scp.walk_motion_3d.v2" and p["coordinate_basis"] == "GLTF_RH_Y_UP_UNCALIBRATED"
def cross(a,b):
 return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def rotate(q,v):
 t=[2*x for x in cross(q[:3],v)]
 c=cross(q[:3],t)
 return [v[i]+q[3]*t[i]+c[i] for i in range(3)]
def mul(a,b):
 x,y,z,w=a; A,B,C,D=b
 return [w*A+x*D+y*C-z*B,w*B-x*C+y*D+z*A,w*C+x*B-y*A+z*D,w*D-x*A-y*B-z*C]
maximum=0.
assert len(p["actors"])==2
for i,a in enumerate(p["actors"]):
 ref=oracle["cases"][i]
 assert ref["reached"] and ref["id"]==r["SpatialCaseIDs"][i]
 bones={x["id"]:x for x in a["bones"]}
 for n,f in enumerate(a["frames"]):
  assert f["frame"]==f["time_num"]==n*12 and f["time_den"]==12
  assert f["foot_contact"]=={"state":"unknown"}
  q=f["local_quat_xyzw"]["hip"]
  child=f["local_quat_xyzw"]["knee"]
  for rot in (q,child):
   assert abs(sum(x*x for x in rot)-1)<1e-6
  origin=f["root_xyz"]
  shift=[origin[k]-ref["start"][k] for k in range(3)]
  knee=[origin[k]+rotate(q,bones["knee"]["rest"])[k] for k in range(3)]
  lower=rotate(mul(q,child),bones["ankle"]["rest"])
  end=[knee[k]+lower[k] for k in range(3)]
  expected_knee=[ref["knee"][k]+shift[k] for k in range(3)]
  expected_end=[ref["end"][k]+shift[k] for k in range(3)]
  error=max(math.dist(knee,expected_knee),math.dist(end,expected_end))
  maximum=max(maximum,error)
  assert error<=1e-8,("ORIGINAL_SOURCE_FK",a["id"],n,error)
print("W16B2_THIRD_NUMERIC_SOURCE_FK_PASS",maximum)
