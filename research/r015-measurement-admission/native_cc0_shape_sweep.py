"""R015 real evaluated MakeHuman/MPFB native human body shape-key DOE.

The source is an actual full adult CC0/MPFB .blend, not a synthetic numerical
proxy. Geometry is explicitly Blender units, never fabricated centimeters,
BMI, age, sex, ethnicity, clinical morphology, or external anatomy approval.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
import numpy as np

ap=argparse.ArgumentParser()
ap.add_argument("--sex",choices=("female","male"),required=True)
ap.add_argument("--native-source",type=Path,required=True)
ap.add_argument("--source-receipt",type=Path,required=True)
ap.add_argument("--out",type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
assert Path(bpy.data.filepath).resolve()==a.native_source.resolve()
a.out.mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for block in iter(lambda:f.read(1<<20),b""):h.update(block)
 return h.hexdigest()
source=json.loads(a.source_receipt.read_text())
assert source["sex_macro"]==a.sex and source["status"]=="PASS_BOUNDED_REAL_SOURCE_NATIVE_TEMPORAL_EVIDENCE_CAPTURE_ONLY"
assert sha(a.native_source)==source["native_scene"]["sha256"],"source input no longer bound to original source-native receipt"
body=bpy.data.objects["R014_"+a.sex+"_textured_body"]
rig=bpy.data.objects["R014_"+a.sex+"_textured_rig"]
assert body.type=="MESH" and rig.type=="ARMATURE"
assert len(rig.data.bones)==163 and len(body.data.vertices)>=13000
assert body.data.shape_keys
keys=list(body.data.shape_keys.key_blocks)
assert len(keys)==(30 if a.sex=="female" else 20)
scene=bpy.context.scene
scene.frame_set(2)
bpy.context.view_layer.update()
shape_names=[k.name for k in keys if k.name.lower()!="basis"]
assert len(shape_names)>=18

# Source stable native topology, sampled world-space geometry after evaluated
# original shape keys and actual source rig skin deformation.
def geometry():
 dg=bpy.context.evaluated_depsgraph_get()
 obj=body.evaluated_get(dg)
 mesh=obj.to_mesh()
 try:
  points=np.asarray([list(obj.matrix_world@v.co) for v in mesh.vertices],dtype=np.float64)
  polygons=[tuple(p.vertices) for p in mesh.polygons]
 finally:
  obj.to_mesh_clear()
 assert points.shape==(len(body.data.vertices),3) and np.isfinite(points).all()
 bbox_min=points.min(axis=0);bbox_max=points.max(axis=0)
 extent=bbox_max-bbox_min
 assert np.isfinite(extent).all() and np.min(extent)>.01
 # Deliberate uncalibrated cross-section proxy: slice vertices at 3
 # height quantiles. Torso/arm separation and true perimeter UNKNOWN.
 sections={}
 for h in (.43,.56,.68):
  mid=float(bbox_min[2]+h*extent[2])
  window=max(float(extent[2])*.022,.012)
  strip=points[np.abs(points[:,2]-mid)<=window,:]
  if len(strip)>=10:
   sections[str(h)]={"sample_vertex_count":len(strip),
       "entire_body_slice_xspan_Blender":float(np.ptp(strip[:,0])),
       "entire_body_slice_yspan_Blender":float(np.ptp(strip[:,1]))}
  else:
   sections[str(h)]={"sample_vertex_count":len(strip),
       "status":"UNKNOWN_INSUFFICIENT_VERTICES"}
 return points,polygons,extent,sections

baseline,polygons,ext0,sections0=geometry()
tri=np.asarray([(p[0],p[j],p[j+1]) for p in polygons for j in range(1,len(p)-1)],dtype=np.int32)
assert len(tri)>20000
n0=np.cross(baseline[tri[:,1]]-baseline[tri[:,0]],baseline[tri[:,2]]-baseline[tri[:,0]])
m0=np.linalg.norm(n0,axis=1)
assert np.all(np.isfinite(m0))
original_values={k.name:float(k.value) for k in keys}
steps=[]
maximum_roundtrip=0.0
for key in keys:
 if key.name.lower()=="basis":continue
 original=original_values[key.name]
 for sign in (-1.,1.):
  target=max(float(key.slider_min),min(float(key.slider_max),original+sign*.10))
  if abs(target-original)<.01:continue
  key.value=target
  bpy.context.view_layer.update()
  points,poly,extent,section=geometry()
  assert poly==polygons,"shape slider modified topology"
  norms=np.cross(points[tri[:,1]]-points[tri[:,0]],points[tri[:,2]]-points[tri[:,0]])
  mags=np.linalg.norm(norms,axis=1)
  dis=np.linalg.norm(points-baseline,axis=1)
  dot=np.einsum("ij,ij->i",n0,norms)
  inversions=int(np.count_nonzero((m0>1e-11)&(dot<=0)))
  collapses=int(np.count_nonzero((m0>1e-11)&(mags<.10*m0)))
  steps.append({
    "key":key.name,"original_value":original,"test_value":target,
    "native_slider_delta":target-original,
    "max_mesh_vertex_displacement_Blender":float(dis.max()),
    "p95_mesh_vertex_displacement_Blender":float(np.percentile(dis,95)),
    "mesh_bbox_extent_Blender":extent.tolist(),
    "bbox_extent_delta_Blender":(extent-ext0).tolist(),
    "entire_body_cross_section_proxies":section,
    "inverted_sampled_native_triangles":inversions,
    "severely_collapsed_sampled_triangles":collapses,
    "source_unit_status":"UNCALIBRATED_BLENDER_SCENE_UNITS"}
  )
  key.value=original
  bpy.context.view_layer.update()
  recovered,p2,e2,s2=geometry()
  assert p2==polygons
  err=float(np.max(np.linalg.norm(recovered-baseline,axis=1)))
  maximum_roundtrip=max(maximum_roundtrip,err)
  assert err<1e-5, "native source mesh shape key failed strict return control"
assert len(steps)>25
assert all(float(k.value)==original_values[k.name] for k in keys)
worst=max(steps,key=lambda x:x["max_mesh_vertex_displacement_Blender"])
anyfold=any(x["inverted_sampled_native_triangles"] or x["severely_collapsed_sampled_triangles"] for x in steps)
anyempty=any(x["max_mesh_vertex_displacement_Blender"]<1e-8 for x in steps)
r={
 "schema":"r015.real_cc0_native_morph_shape_key_doe.v1",
 "research_status":"PASS_TRUE_NATIVE_EVALUATED_MESH_SWEEP_ONLY",
 "production_morphology":"HOLD_NATIVE_UNITS_ANTHROPOMETRY_AGE_SEX_OOD_ANATOMY",
 "source_original_cc0_scene_sha256":sha(a.native_source),
 "source_original_cc0_receipt_sha256":sha(a.source_receipt),
 "source_original_type":"R014 original CC0/MPFB full human, source actual Blender rig",
 "sex_macro_file_label":a.sex,
 "sex_identity_or_biological_marker_inference":"NONE; this only identifies original source preset filename",
 "mesh_vertices":len(baseline),"triangle_fans":len(tri),
 "source_rig_bones":len(rig.data.bones),"native_shape_keys":len(keys),
 "original_source_scene_world_to_centimetres":"UNKNOWN_NOT_INDEPENDENTLY_CALIBRATED",
 "baseline_evaluated_bbox_extent_Blender":ext0.tolist(),
 "baseline_uncalibrated_whole_body_section_proxies":sections0,
 "actual_native_shape_parameter_samples":steps,
 "tested_shape_cases":len(steps),
 "negative_or_noop_deformations_present":anyempty,
 "triangle_or_area_anomalies_present":anyfold,
 "max_reversibility_error_Blender":maximum_roundtrip,
 "largest_evaluated_shape_change":worst,
 "physical_source_measurement_admission":"UNKNOWN_ABSTAIN",
 "independent_heldout_body_types":"NOT_TESTED",
 "full_anatomy":"EXTERNAL_REGION_MESH_COVERAGE_REQUIRES_HUMAN_AND_LANDMARK_VALIDATION",
 "native_animation_root_or_contact":"NOT_TESTED_IN_THIS_MORPH_EXPERIMENT",
 "rights":"original MPFB/MakeHuman CC0 core; bundled component licenses verified separately",
 "limits":[
   "Measured 3D geometry is real native evaluated Blender skin, but all distances are original Blender units",
   "Extrema and entire-body slices can include arms, hair, legs and hidden helper topology, not anatomical circumferences",
   "Source shape key names are opaque, do not establish age, sex, genetic body categories or validated fat/muscle controls",
   "No outside measured scale reference, independently defined anatomical landmarks, mesh section-loop circumferences",
   "No simultaneous multikey OOD holdout, deformed tissue simulation, skin texture or cinematic model acceptance"]
}
out=a.out/(a.sex+"_native_real_morph_doe.json")
out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
print("R015_REAL_NATIVE_MORPH_SWEEP",json.dumps({
  "preset":a.sex,"vertex_count":len(baseline),"keys":len(keys),"cases":len(steps),
  "maximum_roundtrip":maximum_roundtrip,"anyfold":anyfold,
  "largest_change":worst["max_mesh_vertex_displacement_Blender"],
  "status":r["research_status"]},sort_keys=True),flush=True)
