"""R014 rights-preserving actual MHR skin weight differential. Aggregate only."""
import argparse, collections, json, math, sys
from pathlib import Path
import bpy
import numpy as np

p=argparse.ArgumentParser()
for flag in ("motion","native-source","numeric-receipt","out"):p.add_argument("--"+flag,required=True)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
assert a.motion in ("07_01","07_02")
assert Path(bpy.data.filepath).resolve()==Path(a.native_source).resolve()
s=json.loads(Path(a.numeric_receipt).read_text())
assert s["status"]=="HOLD_NATIVE_GAIT_ANATOMY_AND_CINEMATIC_VIDEO"
assert s["original_source_motion"]==a.motion and s["variant"]=="neutral"
assert s["derived_full_animation_artifact_distribution"]=="WITHHELD_SOURCE_RIGHTS_VENUE_GATE"
assert s["source_mesh_vertices"]==18439 and s["source_rig_bones"]==126
rig=bpy.data.objects["R014_MHR_neutral_rig"];body=bpy.data.objects["R014_MHR_neutral_body"]
assert body.parent is rig and len(body.data.vertices)==18439 and len(rig.data.bones)==126
tri=np.asarray([(int(f.vertices[0]),int(f.vertices[j]),int(f.vertices[j+1]))
 for f in body.data.polygons for j in range(1,len(f.vertices)-1)],dtype=np.int32)
assert tri.shape==(36874,3)
bones={b.name for b in rig.data.bones}
groupnames={g.index:g.name for g in body.vertex_groups}
inf=[]
for v in body.data.vertices:
    weights={groupnames.get(i.group,""):float(i.weight) for i in v.groups
             if groupnames.get(i.group,"") in bones and i.weight>1e-10}
    assert all(math.isfinite(w) for w in weights.values())
    inf.append(weights)
def stats(vals):
    if not vals:return {"count":0}
    t=np.asarray(vals,dtype=np.float64)
    return {"count":int(t.size),"min":float(t.min()),"median":float(np.median(t)),
      "p95":float(np.percentile(t,95)),"max":float(t.max()),"mean":float(t.mean())}
def face_group(fid):
    w=collections.defaultdict(float)
    for vid in tri[fid]:
        for name,weight in inf[int(vid)].items():w[name]+=weight
    return max(w,key=w.get) if w else "UNBOUND"
dominant=[face_group(i) for i in range(len(tri))]
def weights_of(faceids):
    if not faceids:return {"vertices":0}
    verts=np.unique(tri[np.asarray(sorted(faceids),dtype=np.int32)].ravel())
    sums=[];n=[];right=[];root=[];twist=[];opp=[]
    for v in verts:
        w=inf[int(v)]
        sums.append(sum(w.values()));n.append(len(w))
        right.append(w.get("r_lowleg",0))
        root.append(w.get("root",0))
        twist.append(sum(val for name,val in w.items() if name.startswith("r_lowleg") and "twist" in name))
        opp.append(w.get("l_lowleg",0))
    return {"vertices":len(verts),"sum_weights":stats(sums),
      "influence_count":stats(n),"r_lowleg_weight":stats(right),
      "root_weight":stats(root),"right_lowleg_twist_weight":stats(twist),
      "opposite_lowleg_weight":stats(opp),
      "nonunit_weight_sum_vertices":sum(abs(x-1)>.01 for x in sums),
      "over_four_influences_vertices":sum(x>4 for x in n)}
def geometry():
    ob=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=ob.to_mesh()
    try:
        inverse=rig.matrix_world.inverted_safe()
        points=np.asarray([list(inverse@(ob.matrix_world@v.co)) for v in mesh.vertices],dtype=np.float64)
        polygons=[tuple(int(k) for k in f.vertices) for f in mesh.polygons]
    finally:ob.to_mesh_clear()
    assert points.shape==(18439,3) and np.isfinite(points).all()
    assert polygons==[tuple(int(k) for k in f.vertices) for f in body.data.polygons]
    return points
def normal_size(x):
    b=x[tri[:,1]]-x[tri[:,0]];c=x[tri[:,2]]-x[tri[:,0]]
    return np.linalg.norm(np.cross(b,c),axis=1)
inverse=rig.matrix_world.inverted_safe()
raw=np.asarray([list(inverse@(body.matrix_world@v.co)) for v in body.data.vertices],dtype=np.float64)
raw_areas=normal_size(raw)
assert raw_areas.min()>1e-11
scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
first_areas=normal_size(geometry())
assert first_areas.min()>1e-11
first_union=set();raw_union=set();first_counts=collections.Counter();raw_counts=collections.Counter()
rotation=collections.defaultdict(list)
sample_frames={int(i):v for i,v in s["skin_geometry_samples"].items()}
controls=[n for n in bones if n.startswith(("r_lowleg","r_foot","r_ball","root","r_subtalar","r_transversetarsal"))]
assert "r_lowleg" in controls and "root" in controls
for frame in range(1,s["gait_frames"]+1):
    scene.frame_set(frame);bpy.context.view_layer.update()
    area=normal_size(geometry())
    f=set(int(i) for i in np.flatnonzero(area<.1*first_areas))
    r=set(int(i) for i in np.flatnonzero(area<.1*raw_areas))
    if frame in sample_frames:assert len(f)==sample_frames[frame]["severe_area_collapse"]
    first_union.update(f);raw_union.update(r)
    first_counts.update(dominant[i] for i in f)
    raw_counts.update(dominant[i] for i in r)
    for n in controls:
        pb=rig.pose.bones[n]
        q=(pb.matrix@rig.data.bones[n].matrix_local.inverted_safe()).to_quaternion()
        angle=float(q.angle)
        rotation[n].append(min(angle,2*math.pi-angle))
combined=first_union|raw_union
bad_group=collections.defaultdict(set)
for i in combined:bad_group[dominant[i]].add(i)
untouched_groups=collections.defaultdict(set)
for i,g in enumerate(dominant):
    if i not in combined and g in ("r_lowleg","root","l_lowleg"):
        untouched_groups[g].add(i)
report={
 "schema":"r014.mhr_source_skin_influence_integrity.v1",
 "status":"HOLD_REAL_HUMAN_SKIN_AND_SOURCE_RIGHTS",
 "motion":a.motion,"source_asf_sha256":s["original_source_asf_sha256"],
 "source_amc_sha256":s["original_source_amc_sha256"],
 "actual_blender_frame_count":s["gait_frames"],
 "mesh_vertices":18439,"rig_bones":126,"triangles":36874,
 "reference":"raw MHR body.data and first captured pose are reference PROXIES, NOT CERTIFIED BIND",
 "unique_collapsed_faces_vs_first_frame":len(first_union),
 "unique_collapsed_faces_vs_raw_mesh":len(raw_union),
 "unique_collapsed_faces_both_criteria_across_any_frame":len(first_union&raw_union),
 "collapsed_face_frame_count_by_dominant_group_first_reference":dict(first_counts),
 "collapsed_face_frame_count_by_dominant_group_raw_reference":dict(raw_counts),
 "source_weight_stats_on_union_bad_faces_by_group":{g:weights_of(ids) for g,ids in sorted(bad_group.items())},
 "same_dominant_group_never_collapsed_control_stats":{g:weights_of(ids) for g,ids in sorted(untouched_groups.items())},
 "source_bone_pose_angle_from_rest_radians_DESCRIPTIVE":{n:stats(v) for n,v in sorted(rotation.items())},
 "source_contact":"UNKNOWN_NOT_FORCE_MEASURED",
 "prohibited_claims":["No full pose, per-frame angle curve, vertex/face ID, media, mesh or native scene output",
    "No anatomical bind-pose certification", "No physical tissue / ROM/contact or skin quality pass",
    "Source-weight group names are only approximations of anatomy"],
 "disposition":"Research-only M1 hold; source, visual, Product and R009 gates unchanged"
}
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
(out/"r014_mhr_skin_influence_aggregates_ONLY.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print("R014_SOURCE_SKIN_WEIGHT_AUDIT",json.dumps({
 "motion":a.motion,"frames":report["actual_blender_frame_count"],
 "bad_unique_faces":len(combined),"first_groups":dict(first_counts),
 "raw_groups":dict(raw_counts)},sort_keys=True),flush=True)
