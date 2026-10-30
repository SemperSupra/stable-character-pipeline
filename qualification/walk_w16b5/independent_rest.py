"""W16-B5 independent pure-stdlib native-rest source/parent matrix witness."""
import json,math,sys
def matmul(a,b):
 return [sum(a[4*i+k]*b[4*k+j] for k in range(4)) for i in range(4) for j in range(4)]
def apply(a,v):
 return [sum(a[i*4+j]*v[j] for j in range(4)) for i in range(4)]
def norm(a,b):return max(abs(x-y) for x,y in zip(a,b))
def verify(src,native):
 if src["schema"]!="scp.walk_dual_leg_rest_clock.v4" or native["schema"]!="scp.walk_w16b5_native_rest_bridge.v1":
  raise ValueError("B5_WITNESS_SCHEMA")
 if src["rights"]!=native["source_rights"] or src["profile"]!=native["profile"]:
  raise ValueError("B5_WITNESS_RIGHTS_SOURCE")
 if len(native["actors"])!=2:raise ValueError("B5_ACTOR_COUNT")
 max_error=0;non_equiv=0
 for i,(a,s) in enumerate(zip(native["actors"],src["actors"])):
  if a["actor_id"]!=s["id"] or len(a["bones"])!=4:raise ValueError("B5_ACTOR_BONES")
  named={b["id"]:b for b in a["bones"]}
  if len(named)!=4:raise ValueError("B5_BONE_DUPLICATE")
  for b,srcb in zip(a["bones"],s["rest_bones"]):
   if b["id"]!=srcb["id"] or b["parent"]!=srcb["parent"]:
    raise ValueError("B5_PARENT_ID")
   m=b["native_world_rest_rowmajor"]
   local=b["native_parent_local_rest_rowmajor"]
   if len(m)!=16 or len(local)!=16 or any(not math.isfinite(x) for x in m+local):
    raise ValueError("B5_NONFINITE_MATRIX")
   if norm(m[12:],[0,0,0,1])>1e-6 or norm(local[12:],[0,0,0,1])>1e-6:
    raise ValueError("B5_AFFINE_MATRIX")
   got_head=apply(m,[0,0,0,1])[:3]
   got_tail=apply(m,[0,.6,0,1])[:3]
   err=max(norm(got_head,srcb["rest_head"]),norm(got_tail,srcb["rest_tail"]))
   max_error=max(max_error,err)
   if err>1e-6:raise ValueError("B5_NATIVE_REST_TRANSFORM_FALSE")
   expected=m if not b["parent"] else matmul(named[b["parent"]]["native_world_rest_rowmajor"],local)
   err=norm(expected,m);max_error=max(max_error,err)
   if err>1e-6:raise ValueError("B5_NATIVE_PARENT_LOCAL_CHAIN")
   computed=norm(m,srcb["world_rest_bind_rowmajor"])<1e-6
   if computed!=b["source_matrix_equals_actual_native"]:
    raise ValueError("B5_FAKE_NATIVE_EQUALITY_STATUS")
   non_equiv+=int(not computed)
 if non_equiv<1:raise ValueError("B5_BAD_ASSUMPTION_SOURCE_EQUALS_BLENDER_REST")
 return {"schema":"scp.walk_w16b5_third_native_rest_oracle.v1","status":"PASS_NATIVE_MATRIX_PARENT_BASIS_NOT_B4_IDENTITY",
  "source_sha256":src["source_sha256"],"profile":src["profile"],
  "maximum_matrix_source_world_error":max_error,"non_equivalent_rest_basis_count":non_equiv,
  "scope":"ORIGINAL_SKELETON_REST_ONLY_NOT_GROUNDED_NATIVE_MESH"}
def main():
 import pathlib
 src=json.loads(pathlib.Path(sys.argv[1]).read_text())
 nat=json.loads(pathlib.Path(sys.argv[2]).read_text())
 r=verify(src,nat)
 pathlib.Path(sys.argv[3]).write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
 print("W16B5_THIRD_REST_MATRIX_FK_PASS",r["maximum_matrix_source_world_error"],r["non_equivalent_rest_basis_count"])
if __name__=="__main__":main()
