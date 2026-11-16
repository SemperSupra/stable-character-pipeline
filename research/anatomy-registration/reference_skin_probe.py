"""R036 HRA male skin+lung same-reference → actual MPFB external source probe.

Fits only global signed-axis rotations, uniform scale and translation against
visible MPFB surface. It deliberately DOES NOT claim landmark-confirmed
nonrigid anatomical registration or organ-body collision correctness.
Source donor geometry is CC BY 4.0, SHA captured and source-locked in CI.
"""
import bpy
import argparse
import hashlib
import itertools
import json
import math
import os
import sys
from mathutils import Vector, Matrix, kdtree

SOURCE_LUNG="e64351b72b0bc5289a4dc32ba2b402b9c974f9ec0b1972bf06b436864f917913"
def args():
 p=argparse.ArgumentParser()
 p.add_argument("--stage",choices=("inspect","verify"),required=True)
 p.add_argument("--skin",default="")
 p.add_argument("--lung",default="")
 p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])

def fail(message):
 print("R036_REGISTRATION_FAIL",message)
 raise RuntimeError(message)
def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()
def points(ob,max_samples=3500,include_all_bounds=True):
 if not ob:fail("no source model objects")
 num=sum(len(o.data.vertices) for o in ob)
 if num<=0:fail("empty source model")
 stride=max(1,math.ceil(num/max_samples))
 low=[float("inf")]*3;high=[float("-inf")]*3
 samples=[];index=0
 for o in ob:
  if o.type!="MESH":continue
  mat=o.matrix_world.copy()
  for v in o.data.vertices:
   pt=mat@v.co
   if not all(math.isfinite(z) for z in pt):fail("nonfinite source point")
   if include_all_bounds:
    for ax in range(3):
     low[ax]=min(low[ax],pt[ax])
     high[ax]=max(high[ax],pt[ax])
   if index%stride==0 and len(samples)<max_samples:samples.append(pt.copy())
   index+=1
 if not include_all_bounds:
  for pt in samples:
   for ax in range(3):
    low[ax]=min(low[ax],pt[ax]);high[ax]=max(high[ax],pt[ax])
 if len(samples)<10:fail("too few source samples")
 return {"source_vertices":num,"low":low,"high":high,"samples":samples,
  "center":Vector([(low[i]+high[i])/2 for i in range(3)]),
  "size":[high[i]-low[i] for i in range(3)]}

def eval_body_points(obj,max_samples=3500):
 bpy.context.view_layer.update()
 active=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
 mesh=active.to_mesh()
 try:
  mat=active.matrix_world.copy()
  pts=[mat@v.co for v in mesh.vertices]
  if not pts:fail("empty evaluated MakeHuman body")
  stride=max(1,math.ceil(len(pts)/max_samples))
  samples=pts[::stride][:max_samples]
  low=[min(p[i] for p in pts) for i in range(3)]
  high=[max(p[i] for p in pts) for i in range(3)]
  return {"source_vertices":len(pts),"low":low,"high":high,
   "samples":samples,"center":Vector([(low[i]+high[i])/2 for i in range(3)]),
   "size":[high[i]-low[i] for i in range(3)]}
 finally:active.to_mesh_clear()

def permutation_sign(perm):
 n=0
 for i in range(3):
  for j in range(i+1,3):
   if perm[i]>perm[j]:n+=1
 return -1 if n%2 else 1

def rot(pt,perm,sign):
 return Vector((sign[0]*pt[perm[0]],sign[1]*pt[perm[1]],sign[2]*pt[perm[2]]))

def nearest_metrics(pts,tree):
 d=sorted(tree.find(pt)[2] for pt in pts)
 n=len(d)
 return {"mean_m":sum(d)/n,"p50_m":d[min(n-1,math.ceil(n*.5)-1)],
  "p95_m":d[min(n-1,math.ceil(n*.95)-1)],"max_m":d[-1]}

def kd(pts):
 tree=kdtree.KDTree(len(pts))
 for i,p in enumerate(pts):tree.insert(p,i)
 tree.balance()
 return tree

def align(source,target):
 target_tree=kd(target["samples"])
 results=[]
 for perm in itertools.permutations((0,1,2)):
  for sign in itertools.product((-1,1),repeat=3):
   determinant=permutation_sign(perm)*sign[0]*sign[1]*sign[2]
   source_z_extent=source["size"][perm[2]]
   if source_z_extent<=.01:fail("reference skin flat or bad scale")
   scale=target["size"][2]/source_z_extent
   rotated=[rot(p-source["center"],perm,sign)*scale+target["center"] for p in source["samples"]]
   a=nearest_metrics(rotated,target_tree)
   b=nearest_metrics(target["samples"],kd(rotated))
   # Penalize both source differences and uncovered target surface. This is a
   # cross-point-cloud coarse rigid fitting score, NOT anatomy correctness.
   score=a["p95_m"]+.5*b["p95_m"]
   results.append({"permutation":list(perm),"sign":list(sign),
    "determinant":determinant,"scale":scale,
    "score_m":score,"reference_to_mpfb":a,"mpfb_to_reference":b})
 results.sort(key=lambda r:(r["score_m"],r["permutation"],r["sign"]))
 proper=next(x for x in results if x["determinant"]==1)
 improper=next(x for x in results if x["determinant"]==-1)
 return proper,improper,results

def transformed(pts,source,target,solution):
 return [rot(p-source["center"],solution["permutation"],solution["sign"])*solution["scale"]+target["center"] for p in pts]

def inside_aabb(points,low,high):
 count=sum(all(low[i]<=p[i]<=high[i] for i in range(3)) for p in points)
 return count/len(points)

def import_glb(path):
 if not path or not os.path.isfile(path):fail("missing donor GLB")
 if os.path.getsize(path)>70_000_000:fail("donor GLB exceeds admitted per-asset limit")
 with open(path,"rb") as f:
  if f.read(4)!=b"glTF":fail("invalid donor GLB magic")
 before=set(bpy.context.scene.objects)
 bpy.ops.import_scene.gltf(filepath=path)
 new=[o for o in bpy.context.scene.objects if o not in before]
 meshes=sorted([o for o in new if o.type=="MESH" and len(o.data.vertices)>0],key=lambda o:o.name)
 if not meshes:fail("donor import generated no real meshes")
 return new,meshes

def matrix_from_alignment(source,target,candidate):
 perm,sign=candidate["permutation"],candidate["sign"]
 m=Matrix.Identity(4)
 for r in range(3):
  for col in range(3):m[r][col]=candidate["scale"]*sign[r]*(1 if perm[r]==col else 0)
 translation=target["center"]-rot(source["center"],perm,sign)*candidate["scale"]
 for i in range(3):m[i][3]=translation[i]
 return m

def inspect(ns):
 if not ns.skin or not ns.lung:fail("source reference skin and lung required")
 if sha(ns.lung)!=SOURCE_LUNG:fail("CCF lung source SHA mismatch")
 body=bpy.data.objects.get("R036_Official_MPFB_Human")
 rig=bpy.data.objects.get("R036_Official_MPFB_Rig")
 if body is None or rig is None or len(rig.data.bones)!=163:fail("actual MPFB source character unavailable")
 bpy.context.scene.frame_set(1)
 official=eval_body_points(body)
 added_skin,skin_meshes=import_glb(ns.skin)
 skin=points(skin_meshes,max_samples=3200)
 if skin["source_vertices"]<1000:fail("skin donor source too small")
 added_lung,lung_meshes=import_glb(ns.lung)
 lung=points(lung_meshes,max_samples=1600)
 original_source_lung_fraction=inside_aabb(lung["samples"],skin["low"],skin["high"])
 proper,improper,ranked=align(skin,official)
 sampled_lung_transformed=transformed(lung["samples"],skin,official,proper)
 mapped_lung_fraction=inside_aabb(sampled_lung_transformed,official["low"],official["high"])
 old_lungs=[o for o in bpy.context.scene.objects if o.name.startswith("R036_HRA_Lung_") and o.type=="MESH"]
 old_center=None
 if old_lungs:
  old_centers=points(old_lungs,max_samples=1000)
  old_center=[float(x) for x in old_centers["center"]]
 candidate_center=sum(sampled_lung_transformed,Vector())/len(sampled_lung_transformed)
 # Create NEW separate derived reference candidate. Leave the original
 # MakeHuman rig, skin, and the #555 provisional donor scene untouched.
 transform=matrix_from_alignment(skin,official,proper)
 root=bpy.data.objects.new("R036_HRA_SkinAligned_Candidate_UNVALIDATED",None)
 bpy.context.collection.objects.link(root);root.matrix_world=transform
 root["source_skin_sha256"]=sha(ns.skin)
 root["source_lung_sha256"]=SOURCE_LUNG
 root["fit_model"]="discrete_24_proper_axis_rotation+height_scale+center_translate"
 root["fit_medical_validity"]="UNQUALIFIED"
 root["fit_determinant"]=1
 registered=0
 for part in lung_meshes:
  world=part.matrix_world.copy()
  local=[world@v.co for v in part.data.vertices]
  faces=[list(poly.vertices) for poly in part.data.polygons]
  if not faces:continue
  new=bpy.data.meshes.new("R036_HRA_Candidate_SourceMesh_"+str(registered))
  new.from_pydata(local,[],faces);new.update()
  obj=bpy.data.objects.new("R036_HRA_Candidate_Lung_"+str(registered),new)
  bpy.context.collection.objects.link(obj)
  obj.parent=root
  obj["source_sha256"]=SOURCE_LUNG
  obj["source_license"]="CC BY 4.0, HuBMAP CCF 3D Reference Object Library"
  obj["reference_frame"]="HRA Skin Male v1.2 coarse registration candidate"
  obj["medical_fit"]="NOT_ADMITTED"
  registered+=1
 for original in added_skin+added_lung:
  if original.name in bpy.data.objects:bpy.data.objects.remove(original,do_unlink=True)
 if registered==0:fail("no real donor lung mesh saved")
 os.makedirs(ns.out,exist_ok=True)
 scene=bpy.context.scene
 scene.frame_set(1)
 blend=os.path.join(ns.out,"mpfb-hra-skin-registration-candidate.blend")
 bpy.ops.wm.save_as_mainfile(filepath=blend,check_existing=False)
 result={
   "schema":"scp.anatomy.hra_skin_reference.registration_probe.v1",
   "status":"PASS_COARSE_SOURCE_FRAME_PROBE_NOT_ANATOMICAL_FIT",
   "source_skin_sha256":sha(ns.skin),"source_lung_sha256":SOURCE_LUNG,
   "source_skin_mesh_count":len(skin_meshes),"source_skin_vertices":skin["source_vertices"],
   "source_lung_mesh_count":len(lung_meshes),"source_lung_vertices":lung["source_vertices"],
   "mpfb_evaluated_skin_vertices":official["source_vertices"],
   "skin_source_bbox_m":skin["size"],"source_lung_bbox_m":lung["size"],
   "mpfb_body_bbox_m":official["size"],"source_raw_lung_fraction_within_skin_AABB":original_source_lung_fraction,
   "best_proper":proper,"best_mirrored":improper,
   "mirror_challenger_lower_score":improper["score_m"]<proper["score_m"],
   "trial_count":len(ranked),"registered_candidate_meshes":registered,
   "mapped_lung_sample_inside_body_AABB_fraction":mapped_lung_fraction,
   "mapped_lung_sample_centroid_m":[float(x) for x in candidate_center],
   "old_spine01_preview_bbox_center_m":old_center,
   "registration_source_method":"global coarse height scaling + center alignment + discrete 24 proper orientations; NO landmarks/ICP yet",
   "anatomical_landmark_validation":"NOT_RUN","inside_real_skin_test":"NOT_RUN",
   "collision_geometry":"NOT_RUN","physical_organ_deformation":"NOT_RUN",
   "skin_lung_source_correspondence":"MEASURED_AABB_ONLY",
   "scene_sha256":sha(blend),
   "license":"HRA CCF 3D Reference Object Library v1.2 CC BY 4.0"
 }
 with open(os.path.join(ns.out,"registration-receipt.json"),"w") as f:json.dump(result,f,sort_keys=True,indent=2)
 print("R036_HRA_SKIN_REG_RECEIPT "+json.dumps(result,sort_keys=True,separators=(",",":")))

def verify(ns):
 root=bpy.data.objects.get("R036_HRA_SkinAligned_Candidate_UNVALIDATED")
 rig=bpy.data.objects.get("R036_Official_MPFB_Rig")
 if root is None or rig is None or len(rig.data.bones)!=163:fail("saved reference candidate/MPFB authority lost")
 meshes=[o for o in bpy.context.scene.objects if o.type=="MESH" and o.name.startswith("R036_HRA_Candidate_Lung_")]
 if len(meshes)<10:fail("source atlas meshes disappeared after Blender reopen")
 for obj in meshes:
  if obj.parent!=root or obj.get("source_sha256")!=SOURCE_LUNG or obj.get("medical_fit")!="NOT_ADMITTED":fail("source donor derived mesh lost provenance or parent")
 if not os.path.isfile(os.path.join(ns.out,"registration-receipt.json")):fail("source receipt missing")
 with open(os.path.join(ns.out,"registration-receipt.json")) as f:original=json.load(f)
 if len(meshes)!=original["registered_candidate_meshes"]:fail("source geometry inventory changed")
 print("R036_HRA_SKIN_REG_VERIFY "+json.dumps({"status":"PASS_CANDIDATE_REOPEN_NARROW","registered_submeshes":len(meshes),
   "bone_count":len(rig.data.bones),"source_skin_sha256":root.get("source_skin_sha256"),
   "medical_registration":"HOLD","physics":"NOT_RUN"},sort_keys=True))
if __name__=="__main__":
 ns=args()
 if ns.stage=="inspect":inspect(ns)
 else:verify(ns)
