"""Source-native MHR skin foldover/anatomical weight-group investigation.

Reopens ephemeral source CMU07 measured walking rig created in current runner.
Only publishes group/height bucket aggregates and source SHA metadata; no
CMU raw 3D trajectory, animated Blender or image-derived human source bytes.
"""
import argparse,collections,hashlib,json,sys
from pathlib import Path
import bpy
import numpy as np

ap=argparse.ArgumentParser()
ap.add_argument("--motion",choices=("07_01","07_02"),required=True)
ap.add_argument("--variant",choices=("neutral","shape20"),required=True)
ap.add_argument("--native-source",type=Path,required=True)
ap.add_argument("--numeric-receipt",type=Path,required=True)
ap.add_argument("--out",type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
a.out.mkdir(parents=True,exist_ok=True)
assert Path(bpy.data.filepath).resolve()==a.native_source.resolve()
source=json.loads(a.numeric_receipt.read_text())
assert source["status"]=="HOLD_NATIVE_GAIT_ANATOMY_AND_CINEMATIC_VIDEO"
assert source["original_source_motion"]==a.motion
assert source["variant"]==a.variant
assert source["capture_contact_provenance"]=="UNKNOWN_NOT_FORCE_MEASURED"
assert source["source_mesh_vertices"]==18439 and source["source_rig_bones"]==126
assert source["derived_full_animation_artifact_distribution"]=="WITHHELD_SOURCE_RIGHTS_VENUE_GATE"
assert source["gait_frames"] in (64,66)
assert source["structural_contact_candidate"] is False
rig=bpy.data.objects["R014_MHR_neutral_rig"]
body=bpy.data.objects["R014_MHR_neutral_body"]
assert body.parent is rig and len(body.data.vertices)==18439
assert len(rig.data.bones)==126
assert len(body.vertex_groups)>10
scene=bpy.context.scene
scene.frame_set(1);bpy.context.view_layer.update()
frame_count=source["gait_frames"]
samples=sorted(set([1,max(2,round(frame_count*.25)),round(frame_count*.5),
                    round(frame_count*.75),frame_count]))
assert len(samples)==5

def skin_local():
    deps=bpy.context.evaluated_depsgraph_get()
    obj=body.evaluated_get(deps)
    mesh=obj.to_mesh()
    try:
        inv=rig.matrix_world.inverted_safe()
        p=np.asarray([list(inv@(obj.matrix_world@v.co)) for v in mesh.vertices],
                     dtype=np.float64)
        polys=[tuple(int(i) for i in face.vertices) for face in mesh.polygons]
    finally:obj.to_mesh_clear()
    assert p.shape==(18439,3) and np.isfinite(p).all()
    return p,polys

rest,polygons=skin_local()
tri=np.asarray([(p[0],p[j],p[j+1]) for p in polygons for j in range(1,len(p)-1)],np.int32)
assert len(tri)==36874
def normals(x):
    v=np.cross(x[tri[:,1]]-x[tri[:,0]],x[tri[:,2]]-x[tri[:,0]])
    return v,np.linalg.norm(v,axis=1)
n0,mag0=normals(rest)
assert np.min(mag0)>1e-11
bone_groups={g.index:g.name for g in body.vertex_groups}
bind_bones=set(b.name for b in rig.data.bones)
def category(name):
    n=name.lower()
    if any(v in n for v in ("foot","toe","ball","tibia","lowleg","upleg","femur","thigh","calf","hip","heel","ankle","knee")):
        return "LOWER_BODY_OR_LEG"
    if any(v in n for v in ("hand","finger","thumb","wrist","forearm","elbow","upperarm","arm","shoulder")):
        return "UPPER_LIMB_HAND"
    if any(v in n for v in ("head","jaw","eye","neck","face","tongue")):
        return "HEAD_FACE_NECK"
    if any(v in n for v in ("spine","pelvis","chest","torso","abdomen","root")):
        return "PELVIS_TORSO"
    return "OTHER_OR_UNCLASSIFIED"
def dominant_bone_for_face(face):
    weights=collections.defaultdict(float)
    for idx in face:
        for group in body.data.vertices[int(idx)].groups:
            name=bone_groups.get(group.group,"")
            if name in bind_bones:weights[name]+=float(group.weight)
    return max(weights,key=weights.get) if weights else "UNBOUND_MESH"
# World transport and source turn should not affect rig-local source geometry.
# Upper/lower rest-height bins are diagnostic only, not anatomical landmarks.
z=rest[:,2]
zmin,zmax=float(z.min()),float(z.max())
assert zmax>zmin
def bucket(c):
    t=(float(c)-zmin)/(zmax-zmin)
    if t<.20:return "height_00_20pct"
    if t<.40:return "height_20_40pct"
    if t<.60:return "height_40_60pct"
    if t<.80:return "height_60_80pct"
    return "height_80_100pct"
results={}
for frame in samples:
    scene.frame_set(frame);bpy.context.view_layer.update()
    x,other=skin_local()
    assert other==polygons
    n,m=normals(x)
    flipped=np.flatnonzero(np.einsum("ij,ij->i",n0,n)<=0)
    collapsed=np.flatnonzero(m<.1*mag0)
    baseline_expected=int(source["skin_geometry_samples"][str(frame)]["inverted_triangles"])
    if len(flipped)!=baseline_expected:
        raise AssertionError("different full 3D source pose: mismatch existing MHR diagnostic foldovers")
    categories=collections.Counter();groups=collections.Counter();heights=collections.Counter()
    for fid in flipped:
        face=tri[int(fid)]
        bone=dominant_bone_for_face(face)
        groups[bone]+=1
        categories[category(bone)]+=1
        heights[bucket(float(np.mean(z[face])))]+=1
    max_abs_motion=np.max(np.linalg.norm((x-rest)*.01,axis=1))
    results[str(frame)]={
       "source_frame":frame,
       "inverted_triangle_count":len(flipped),
       "severely_collapsed_count":len(collapsed),
       "dominant_skin_weight_categories":dict(categories),
       "top_20_source_bone_vertex_groups":groups.most_common(20),
       "original_body_rest_height_buckets":dict(heights),
       "source_bad_face_ids_first_24":[int(i) for i in flipped[:24]],
       "max_geometry_change_relative_to_rig_world_units":float(max_abs_motion),
       "interpretation":"face inversion relative original frame1 skin, NOT self-intersection or clinical injury"}
    print("R014_CMU_SKIN_FOLDOVER_REGION",json.dumps({
       "motion":a.motion,"variant":a.variant,"frame":frame,"inversions":len(flipped),
       "categories":dict(categories),"top_bones":groups.most_common(6)},sort_keys=True),flush=True)
receipt={
  "schema":"r014.motion.cmu07_skin_weight_foldover_atlas.v1",
  "status":"HOLD_MEASURED_CMU_NATIVE_HUMAN_SKIN_TRIANGLE_INVERSION",
  "source_run":43395287795,"source_pr":486,
  "source_motion":a.motion,"variant":a.variant,
  "source_MHR_original_release":"facebookresearch/MHR v1.0.1, 126-bone skinned 18439-vertex body",
  "source_original_amc_sha256":source["original_source_amc_sha256"],
  "source_original_asf_sha256":source["original_source_asf_sha256"],
  "saved_native_blend_sha256_EPHEMERAL_ONLY":hashlib.sha256(a.native_source.read_bytes()).hexdigest(),
  "source_contact":"UNKNOWN_NOT_FORCE_MEASURED",
  "source_entire_data_venue":"original CMU AMC, derived full trajectories/blend remain ephemeral runner-only",
  "source_original_3d_retarget_scope":"pelvis and ankle WORLD positions, not full source joint rotation reproduction",
  "mesh_triangles":len(tri),"source_skin_weight_groups":len(body.vertex_groups),
  "actual_frame_1_based_results":results,
  "hypotheses":[
      "Genuine original hip-knee-foot configuration may require source FK knee pole targets",
      "3-chain MHR IK without source knee/pole constraining can fold anatomical leg even with ankle position exact",
      "MHR LOD1 skin without posed anatomical corrective controls may fold in source-range adult poses",
      "Missing capture root turning and mesh colliding/crossing requires independent visualization"],
  "not_proven":["No foot-contact pressure, source ankle-toe friction or validated gait",
      "Dominant bone weight and source-rest height are region approximations, not clinical anatomy",
      "No head/hair/eyes/face/skin cinematic photoreal improvement from this diagnostic",
      "No hero CC0 source GLB/MPFB retarget, no morphology generalization or CharacterPack canon"],
  "rights_and_release":"R012 source/derivative approval separate; product HOLD; draft unmerged"
}
(a.out/"r014_cmu_skin_foldover_atlas.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
