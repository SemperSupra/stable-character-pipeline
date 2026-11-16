"""R036 real-source coarse ICP challenger: morphology residual investigation.

Fits the actual 92k vertex HRA male reference skin to the actual MPFB evaluated
exterior, preserving proper-handedness and source-to-lung transform. This uses
nearest-vertex residuals, NOT author-validated anatomical landmarks, so the
candidate is ALWAYS UNQUALIFIED for anatomical location and medical truth.
"""
import argparse
import hashlib
import json
import math
import os
import sys
import bpy
import numpy as np
from mathutils import Matrix, Vector, kdtree

SKIN_SHA="8cab299d04323e6364938a271647df5671138a2177f412e741a0d6bd4536ee1c"
LUNG_SHA="e64351b72b0bc5289a4dc32ba2b402b9c974f9ec0b1972bf06b436864f917913"

def fail(reason):
 print("R036_ICP_FAIL",reason)
 raise RuntimeError(reason)
def options():
 p=argparse.ArgumentParser()
 p.add_argument("--stage",choices=("solve","verify"),required=True)
 p.add_argument("--skin",default="")
 p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()
def evaluated(obj,limit=3000):
 bpy.context.view_layer.update()
 ob=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
 mesh=ob.to_mesh()
 try:
  step=max(1,math.ceil(len(mesh.vertices)/limit))
  return np.array([tuple(ob.matrix_world@v.co) for i,v in enumerate(mesh.vertices) if i%step==0][:limit],dtype=np.float64)
 finally:ob.to_mesh_clear()
def imported_skin(path):
 if not os.path.isfile(path) or sha(path)!=SKIN_SHA:fail("wrong or missing HRA exact-source skin GLB")
 initial=set(bpy.context.scene.objects)
 bpy.ops.import_scene.gltf(filepath=path)
 objects=[o for o in bpy.context.scene.objects if o not in initial]
 meshes=[o for o in objects if o.type=="MESH" and len(o.data.vertices)]
 if len(meshes)!=1 or len(meshes[0].data.vertices)!=92659:
  fail("HRA skin topology/mesh inventory changed")
 ob=meshes[0]
 step=max(1,math.ceil(len(ob.data.vertices)/3000))
 samples=np.array([tuple(ob.matrix_world@v.co) for i,v in enumerate(ob.data.vertices) if i%step==0],dtype=np.float64)
 return objects,samples
def to_array(mat):
 return np.array([list(row) for row in mat],dtype=np.float64)
def to_mat(array):
 return Matrix([tuple(row) for row in array.tolist()])
def apply(points,mat):
 return points@mat[:3,:3].T+mat[:3,3]
def tree(points):
 kd=kdtree.KDTree(len(points))
 for i,p in enumerate(points):kd.insert(Vector(tuple(p)),i)
 kd.balance()
 return kd
def match(points,lookup,target):
 idx=[];dist=[]
 for p in points:
  _,i,d=lookup.find(Vector(tuple(p)))
  idx.append(i);dist.append(d)
 return np.asarray(idx),np.asarray(dist),target[np.asarray(idx,dtype=np.int64)]
def metric(a,b):
 kd=tree(b)
 _,d,_=match(a,kd,b)
 return {"mean_m":float(d.mean()),"p50_m":float(np.percentile(d,50)),
  "p95_m":float(np.percentile(d,95)),"max_m":float(d.max()),
  "gt_10mm":int(np.sum(d>.010)),"gt_50mm":int(np.sum(d>.050))}
def score(a,b):
 ab=metric(a,b);ba=metric(b,a)
 return {"s_to_t":ab,"t_to_s":ba,"score_m":ab["p95_m"]+.5*ba["p95_m"]}
def rigid_fit(source,target):
 # Proper Kabsch rotation from matched correspondences. Reject reflections.
 p=source.mean(axis=0);q=target.mean(axis=0)
 h=(source-p).T@(target-q)
 u,_,vt=np.linalg.svd(h)
 fix=np.eye(3)
 if np.linalg.det(vt.T@u.T)<0:fix[2,2]=-1
 rot=vt.T@fix@u.T
 translation=q-rot@p
 return rot,translation
def unit_controls():
 p=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1],[1,2,3]],dtype=np.float64)
 theta=.19
 r=np.array([[math.cos(theta),-math.sin(theta),0],[math.sin(theta),math.cos(theta),0],[0,0,1]])
 goal=p@r.T+np.array([1,2,3])
 got,shift=rigid_fit(p,goal)
 residual=float(np.max(np.linalg.norm(p@got.T+shift-goal,axis=1)))
 if residual>1e-9 or np.linalg.det(got)<.999999:fail("positive-Kabsch unit control failed")
 # Reflected/chiral input must not be considered a proper rigid transform.
 mirror=p.copy();mirror[:,0]*=-1
 no_reflect,tt=rigid_fit(p,mirror)
 error=float(np.max(np.linalg.norm(p@no_reflect.T+tt-mirror,axis=1)))
 if error<.05 or np.linalg.det(no_reflect)<.999999:fail("mirror adversary incorrectly admitted")
 return {"proper_transform_error_m":residual,"reflected_shape_proper_fit_max_residual_m":error}
def solve(source,target,start):
 lookup=tree(target)
 baseline=score(apply(source,start),target)
 best=start.copy()
 winner=baseline
 current=start.copy()
 trace=[]
 for step in range(12):
  mapped=apply(source,current)
  idx,dist,nearest=match(mapped,lookup,target)
  gate=np.percentile(dist,72)
  active=dist<=gate
  if int(np.sum(active))<12:fail("insufficient robust correspondence points")
  # Estimate a small *incremental* rigid adjustment, maintain original
  # source body scale; re-centering or arbitrary shape warps are not allowed.
  rot,translation=rigid_fit(mapped[active],nearest[active])
  before=current.copy()
  delta=np.eye(4);delta[:3,:3]=rot;delta[:3,3]=translation
  candidate=delta@current
  # Include original uniform source height scale but no new scale/reflection.
  r=candidate[:3,:3]
  det=float(np.linalg.det(r))
  prior_scale=float(abs(np.linalg.det(start[:3,:3]))**(1/3))
  if det<=0 or not np.isfinite(det) or abs(det-prior_scale**3)>1e-6:
   fail("ICP changed handedness/scale or produced invalid transform")
  # Compare fitted source vertical axis with baseline and stop before a
  # 25-degree overall rotational change; left-right landmarks still untested.
  orientation=candidate[:3,:3]/prior_scale
  original=start[:3,:3]/prior_scale
  cos_angle=(np.trace(orientation@original.T)-1)/2
  angle=math.degrees(math.acos(float(np.clip(cos_angle,-1,1))))
  if angle>25:break
  trial=score(apply(source,candidate),target)
  trace.append({"iter":step+1,"trim_gate_m":float(gate),"active":int(np.sum(active)),
    "rotation_from_base_deg":angle,"score_m":trial["score_m"]})
  current=candidate
  if trial["score_m"]+1e-8<winner["score_m"]:
   best=candidate.copy();winner=trial
  if float(np.linalg.norm(candidate-before))<1e-8:break
 return baseline,winner,best,trace
def per_band(source,target,mat):
 out={}
 transformed=apply(source,mat)
 lower=float(target[:,2].min());height=float(np.ptp(target[:,2]))
 targettree=tree(target)
 _,dist,_=match(transformed,targettree,target)
 for i in range(6):
  z0=lower+height*i/6;z1=lower+height*(i+1)/6
  selected=dist[(transformed[:,2]>=z0)&(transformed[:,2]<(z1 if i<5 else z1+1e-8))]
  out[str(i)]={"z0_m":z0,"z1_m":z1,"n":len(selected),
    "p95_m":float(np.percentile(selected,95)) if len(selected) else None}
 return out
def run_probe(ns):
 root=bpy.data.objects.get("R036_HRA_SkinAligned_Candidate_UNVALIDATED")
 body=bpy.data.objects.get("R036_Official_MPFB_Human")
 rig=bpy.data.objects.get("R036_Official_MPFB_Rig")
 if root is None or body is None or rig is None or len(rig.data.bones)!=163:fail("R036 560 baseline missing")
 if root.get("source_skin_sha256")!=SKIN_SHA or root.get("source_lung_sha256")!=LUNG_SHA:
  fail("source pin lost on parent")
 parts=[o for o in bpy.context.scene.objects if o.name.startswith("R036_HRA_Candidate_Lung_") and o.type=="MESH"]
 if len(parts)!=67:fail("baseline real lung submeshes missing")
 for ob in parts:
  if ob.parent!=root or ob.get("medical_fit")!="NOT_ADMITTED":fail("baseline no longer explicitly unvalidated")
 controls=unit_controls()
 imported,source=imported_skin(ns.skin)
 target=evaluated(body)
 initial=to_array(root.matrix_world)
 before,after,optimized,trace=solve(source,target,initial)
 if after["score_m"]>before["score_m"]+1e-6:fail("ICP published a worse candidate")
 # Remove HRA reference import, keep existing anatomical candidate hierarchy.
 for ob in imported:
  if ob.name in bpy.data.objects:bpy.data.objects.remove(ob,do_unlink=True)
 root.matrix_world=to_mat(optimized)
 root.name="R036_HRA_ICP_Candidate_UNVALIDATED"
 objective_improved=before["score_m"]-after["score_m"]>1e-5
 root["registration_method"]="robust_trimmed_12_step_Kabsch_proper_fixed_scale" if objective_improved else "BASELINE_PRESERVED_NO_ICP_IMPROVEMENT"
 root["fit_objective_improved"]=objective_improved
 root["anatomic_landmarks_verified"]=False
 root["source_skin_sha256"]=SKIN_SHA
 root["source_lung_sha256"]=LUNG_SHA
 # A close skin fit does not prove lung inside real ribs; source laterality
 # remains held. Derived mesh and original HRA source are not modified.
 bpy.context.view_layer.update()
 os.makedirs(ns.out,exist_ok=True)
 dest=os.path.join(ns.out,"mpfb-hra-icp-candidate.blend")
 bpy.ops.wm.save_as_mainfile(filepath=dest,check_existing=False)
 report={"schema":"scp.anatomy.hra_skin_icp.v1",
  "status":"MEASURED_RIGID_OPTIMIZATION_IMPROVEMENT_ANATOMY_HOLD" if objective_improved else "HOLD_RIGID_ICP_NO_IMPROVEMENT_BASELINE_RETAINED",
  "control":controls,"baseline":before,"best":after,"iterations":trace,
  "baseline_bands":per_band(source,target,initial),
  "best_bands":per_band(source,target,optimized),
  "selected_improvement_m":before["score_m"]-after["score_m"],
  "objective_improved":objective_improved,
  "warning":"Trimmed nearest-vertex inlier score may fall while bidirectional p95 increases; never claim convergence/medical fit from inlier-only decrease",
  "sample_skin_points":len(source),"sample_mpfb_points":len(target),
  "source_skin_sha256":SKIN_SHA,"source_lung_sha256":LUNG_SHA,
  "derived_organ_submeshes":len(parts),"original_source_mesh_immutable":True,
  "laterality":"HOLD_NO_SIDED_LANDMARKS",
  "skin_surface_registration":"HOLD_NO_INDEPENDENT_FIDUCIALS",
  "rib_and_diaphragm_contact":"NOT_RUN",
  "anatomy_and_physics":"NOT_QUALIFIED",
  "saved_blend_sha256":sha(dest)}
 with open(os.path.join(ns.out,"icp-receipt.json"),"w") as f:json.dump(report,f,sort_keys=True,indent=2)
 print("R036_ICP_RECEIPT "+json.dumps(report,sort_keys=True,separators=(",",":")))
def verify(ns):
 root=bpy.data.objects.get("R036_HRA_ICP_Candidate_UNVALIDATED")
 rig=bpy.data.objects.get("R036_Official_MPFB_Rig")
 if not root or not rig or len(rig.data.bones)!=163:fail("saved candidate lost native rig")
 parts=[o for o in bpy.context.scene.objects if o.name.startswith("R036_HRA_Candidate_Lung_") and o.type=="MESH"]
 if len(parts)!=67 or any(o.parent!=root or o.get("medical_fit")!="NOT_ADMITTED" for o in parts):
  fail("saved source candidate organ identity or rights lost")
 if root.get("fit_objective_improved") not in (False,True):fail("missing honest objective improvement receipt")
 if root.get("anatomic_landmarks_verified")!=False or root.get("source_skin_sha256")!=SKIN_SHA:
  fail("saved source candidate falsely admitted")
 print("R036_ICP_VERIFY "+json.dumps({"status":"PASS_REOPEN_CANDIDATE_ONLY","submeshes":len(parts),
  "medical_registration":"HOLD","laterality":"HOLD","tissue_physics":"NOT_RUN"},sort_keys=True))
if __name__=="__main__":
 n=options()
 if n.stage=="solve":run_probe(n)
 else:verify(n)
