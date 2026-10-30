"""Independent pure Python affine 4x4 witness for actual Blender 6-bone rest."""
import hashlib,json,math,sys
from pathlib import Path
def mul(a,b):
 return [sum(a[i*4+k]*b[k*4+j] for k in range(4)) for i in range(4) for j in range(4)]
def p(m,v):
 return [sum(m[i*4+j]*v[j] for j in range(4)) for i in range(4)]
def error(a,b):return max(abs(x-y) for x,y in zip(a,b))
def verify(src,r):
 if r.get("schema")!="scp.walk_w6b5b_native_sixbone_rest.v1" or r.get("source_rights")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC" or r.get("source_sha256")!=hashlib.sha256(src).hexdigest():
  raise ValueError("W6B5B_PROVENANCE_HASH")
 s=json.loads(src)
 if s["profile"]!=r["source_profile"] or s["rights"]!=r["source_rights"] or len(r["actors"])!=2:
  raise ValueError("W6B5B_ACTOR_RIGHTS")
 maxerr=0
 for n,actor in enumerate(r["actors"]):
  if actor["actor"]!=s["actors"][n]["id"] or len(actor["bones"])!=6:
   raise ValueError("W6B5B_NATIVE_TOPOLOGY")
  bones={b["id"]:b for b in actor["bones"]}
  if len(bones)!=6:raise ValueError("W6B5B_DUPLICATE_BONE")
  for bone in actor["bones"]:
   world,local=bone["world_rest_matrix_rowmajor"],bone["parent_local_rest_rowmajor"]
   if len(world)!=16 or len(local)!=16 or not all(math.isfinite(v) for v in world+local):
    raise ValueError("W6B5B_MATRIX_NONFINITE")
   for x in (world,local):
    if error(x[12:],[0,0,0,1])>1e-6:raise ValueError("W6B5B_MATRIX_NONAFFINE")
   derived=world if not bone["parent"] else mul(bones[bone["parent"]]["world_rest_matrix_rowmajor"],local)
   e=error(derived,world);maxerr=max(maxerr,e)
   if e>1e-6:raise ValueError("W6B5B_PARENT_CHAIN_FAKE")
   head=p(world,[0,0,0,1])[:3]
   length=math.dist(bone["expected_head"],bone["expected_tail"])
   tail=p(world,[0,length,0,1])[:3]
   e=max(error(head,bone["expected_head"]),error(tail,bone["expected_tail"]))
   maxerr=max(maxerr,e)
   if e>1e-6:raise ValueError("W6B5B_NATIVE_TAIL_OR_BASIS_ERROR")
   if abs(bone["native_det"]-1)>1e-6:raise ValueError("W6B5B_REFLECTION")
 assert r["knee_rom"]=="UNKNOWN_NO_INDIVIDUAL_OR_SPECIES_JCS_LIMITS"
 return {"schema":"scp.walk_w6b5b_independent_matrix.v1","status":"PASS_SIX_BONE_NATIVE_PARENT_AND_TAIL","max_error":maxerr,"actors":2,"bones":12,"source_sha256":r["source_sha256"],"scope":"REST_ONLY_ROM_UNQUALIFIED"}
if __name__=="__main__":
 src=Path(sys.argv[1]).read_bytes();r=json.loads(Path(sys.argv[2]).read_text())
 out=verify(src,r);Path(sys.argv[3]).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
 print("W6B5B_THIRD_PARENT_MATRIX_PASS",out["max_error"])
