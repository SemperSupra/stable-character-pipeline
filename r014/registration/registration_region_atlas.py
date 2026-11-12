"""R014 source geometry regional registration red-team / color atlas.

Reads only the existing failed Blender Studio CC0 -> MPFB transferred research
scene, without modifying source assets. Labels regions by NEAREST MPFB RIG
BONE SEGMENT as diagnostic proxies, NOT true anatomical correspondences.
No quality pass; emits original failure evidence, action rankings and two real
rendered heatmaps for human review.
"""
import argparse,csv,json,math,sys
from collections import defaultdict
from pathlib import Path
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0,str(Path(__file__).parent))
from registration_math import nearest_segment_region,stats,rgb,bone_region

ap=argparse.ArgumentParser()
ap.add_argument('--sex',required=True,choices=('female','male'))
ap.add_argument('--source',required=True,type=Path)
ap.add_argument('--baseline',required=True,type=Path)
ap.add_argument('--out',required=True,type=Path)
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
args.out.mkdir(parents=True,exist_ok=True)
assert Path(bpy.data.filepath).resolve()==args.source.resolve()
old=json.loads(args.baseline.read_text())
assert old['sex_source_macro']=={'female':0.,'male':1.}[args.sex]
assert old['source_mesh_vertices']==13380 and old['target_mesh_vertices']==10582
source=bpy.data.objects['R014_'+args.sex+'_body_clean_export']
target=bpy.data.objects['GEO-body_'+args.sex+'_realistic']
rigs=[m.object for m in source.modifiers if m.type=='ARMATURE' and m.object]
assert len(rigs)==1
rig=rigs[0]
assert len(rig.data.bones)==163
assert len(source.data.vertices)==13380 and len(target.data.vertices)==10582

bpy.context.view_layer.update()
print('R014_NATIVE_REOPEN_TRANSFORMS',json.dumps({
    'sex':args.sex,
    'source_parent':source.parent.name if source.parent else None,
    'target_parent':target.parent.name if target.parent else None,
    'source_matrix':[[round(x,6) for x in row] for row in source.matrix_world],
    'target_matrix':[[round(x,6) for x in row] for row in target.matrix_world],
    'rig_matrix':[[round(x,6) for x in row] for row in rig.matrix_world],
    'source_modifiers':[m.type for m in source.modifiers],
    'target_modifiers':[m.type for m in target.modifiers],
},sort_keys=True),flush=True)
src=np.array([list(source.matrix_world@v.co) for v in source.data.vertices],dtype=np.float64)
tgt=np.array([list(target.matrix_world@v.co) for v in target.data.vertices],dtype=np.float64)
source.data.calc_loop_triangles()
faces=[list(t.vertices) for t in source.data.loop_triangles]
assert 20000<len(faces)<40000
bvh=BVHTree.FromPolygons([Vector(v.tolist()) for v in src],faces,all_triangles=True)
distances=np.empty(len(tgt),np.float64)
for i,p in enumerate(tgt):
    co,n,poly,d=bvh.find_nearest(Vector(p.tolist()))
    assert co is not None and poly is not None
    distances[i]=d
basep95=float(old['correspondence']['p95_m'])
newp95=float(np.percentile(distances,95))
print('R014_REOPEN_DISTANCES',json.dumps({
 'sex':args.sex,'baseline_p95':basep95,'reopened_p95':newp95,
 'source_min':src.min(axis=0).tolist(),'source_max':src.max(axis=0).tolist(),
 'target_min':tgt.min(axis=0).tolist(),'target_max':tgt.max(axis=0).tolist(),
 'source_centroid':src.mean(axis=0).tolist(),'target_centroid':tgt.mean(axis=0).tolist()
},sort_keys=True),flush=True)
assert abs(newp95-basep95)<.005,('loaded wrong geometric source',basep95,newp95)

# Bone-local rest landmarks in matching Blender scene world coordinates.
segments=[]
for b in rig.data.bones:
    if not bone_region(b.name):continue
    a=rig.matrix_world@b.head_local
    z=rig.matrix_world@b.tail_local
    if (z-a).length>1e-6:
        segments.append((b.name,list(a),list(z)))
labels,names,proxy_dist=nearest_segment_region(tgt,segments)
regions=defaultdict(list)
for i,reg in enumerate(labels):regions[str(reg)].append(i)
region_stats={reg:stats(distances[inds]) for reg,inds in regions.items()}
assert sum(v['count'] for v in region_stats.values())==len(tgt)

# The stored nearest-triangle 4-weight mapping is itself under qualification.
# Count L/R group mismatch as a warning, not as a definitive anatomy finding.
weight_labels=[];cross_sides=defaultdict(lambda:{'total':0,'wrong':0})
for i,v in enumerate(target.data.vertices):
    top=max(v.groups,key=lambda g:g.weight,default=None)
    top_name=target.vertex_groups[top.group].name if top else 'NO_GROUP'
    weight_labels.append(top_name)
    expected=str(names[i]).rsplit('.',1)[-1]
    actual=top_name.rsplit('.',1)[-1]
    if labels[i] in ('hand','arm','leg','foot') and expected in ('L','R') and actual in ('L','R'):
        cross_sides[str(labels[i])]['total']+=1
        if expected!=actual:cross_sides[str(labels[i])]['wrong']+=1

priorities=sorted([
    {'region':k,**v} for k,v in region_stats.items() if v['count']>=20
],key=lambda x:(x['p95_m'],x['fraction_over_50mm']),reverse=True)

# Retain true per-vertex numerical QA for future registration patches.
with (args.out/'per_vertex_registration.csv').open('w',newline='') as f:
    w=csv.writer(f)
    w.writerow(('vertex','world_x','world_y','world_z','distance_to_mpfb_m',
                'nearest_rig_region','nearest_bone','rig_proxy_distance_m','top_transferred_group'))
    for i,p in enumerate(tgt):
        w.writerow((i,*[f'{x:.7f}' for x in p],f'{distances[i]:.7f}',labels[i],names[i],
                    f'{proxy_dist[i]:.7f}',weight_labels[i]))

# Map measured surface mismatch to actual source sculpt mesh loop-corner colors.
# Target topology/UVs are not changed; colors only added to research copy.
target.data=target.data.copy()
channel=target.data.color_attributes.get('R014_registration_distance')
if channel is None:
    channel=target.data.color_attributes.new(name='R014_registration_distance',type='FLOAT_COLOR',domain='CORNER')
for loop in target.data.loops:
    c=rgb(distances[loop.vertex_index])
    channel.data[loop.index].color=(c[0],c[1],c[2],1.0)
mat=bpy.data.materials.new('R014_Registration_Error_Heatmap')
mat.use_nodes=True
nodes=mat.node_tree.nodes
nodes.clear()
out_node=nodes.new('ShaderNodeOutputMaterial')
bsdf=nodes.new('ShaderNodeBsdfPrincipled')
bsdf.inputs['Roughness'].default_value=.87
attr=nodes.new('ShaderNodeAttribute')
attr.attribute_name='R014_registration_distance'
mat.node_tree.links.new(attr.outputs['Color'],bsdf.inputs['Base Color'])
mat.node_tree.links.new(bsdf.outputs['BSDF'],out_node.inputs['Surface'])
target.data.materials.clear();target.data.materials.append(mat)
for obj in bpy.data.objects:
    if obj.type=='MESH':obj.hide_render=(obj!=target)
target.hide_set(False)
for mod in target.modifiers:
    if mod.type in ('ARMATURE','MULTIRES'):
        mod.show_render=False;mod.show_viewport=False

scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.device='CPU'
scene.cycles.samples=10
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=640;scene.render.resolution_y=800
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
world=bpy.data.worlds.new('R014_Registration_Reference_Gray')
world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.8
scene.world=world
key=bpy.data.lights.new('R014_Registration_Softbox','AREA')
lamp=bpy.data.objects.new('R014_Registration_Softbox',key)
bpy.context.collection.objects.link(lamp)
key.energy=600;key.size=5
cam_data=bpy.data.cameras.new('R014_Registration_Heatmap_Camera')
cam=bpy.data.objects.new('R014_Registration_Heatmap_Camera',cam_data)
bpy.context.collection.objects.link(cam);scene.camera=cam
cam_data.type='ORTHO'
lo=tgt.min(axis=0);hi=tgt.max(axis=0);center=(lo+hi)/2;span=hi-lo
cam_data.ortho_scale=max(float(span[2])*1.25,float(span[0])/(640/800)*1.28)
views=[]
for name,sign in [('front',-1),('back',1)]:
    cam.location=(float(center[0]),float(center[1])+sign*5,float(center[2]))
    anchor=Vector(tuple(center.tolist()))
    cam.rotation_euler=(anchor-cam.location).to_track_quat('-Z','Y').to_euler()
    lamp.location=(float(center[0])-1.3,float(center[1])+sign*2,float(center[2])+2)
    bpy.context.view_layer.update()
    projected=[world_to_camera_view(scene,cam,Vector(p.tolist())) for p in tgt[::10]]
    xs=[v.x for v in projected];ys=[v.y for v in projected]
    if min(xs)<.01 or max(xs)>.99 or min(ys)<.01 or max(ys)>.99:
        raise ValueError('camera clips target in '+name+str((min(xs),max(xs),min(ys),max(ys))))
    scene.render.filepath=str(args.out/('error_atlas_'+name+'.png'))
    bpy.ops.render.render(write_still=True)
    assert Path(scene.render.filepath).stat().st_size>10000
    views.append(name)
scene.render.filepath=''
bpy.ops.file.pack_all()
native=args.out/('R014_'+args.sex+'_source_vs_sculpt_registration_error_research.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(native))
assert native.stat().st_size>100000

receipt={
 'status':'HOLD_ANATOMICAL_REGISTRATION_ERROR_LOCALIZED',
 'sex_controlled_preset':old['sex_source_macro'],
 'scene_source':'public GHA 43218606862, failed first-pass MPFB->Studio AABB/nearest-triangle',
 'source_mesh_vertices':len(src),'target_sculpt_base_vertices':len(tgt),
 'source_rig_bones':len(rig.data.bones),'source_triangles':len(faces),
 'global_registration':stats(distances),'old_baseline_p95_m':basep95,
 'regions':region_stats,'ranked_corrective_regions':priorities,
 'approximate_wrong_side_weight_groups':dict(cross_sides),
 'rendered_heatmaps':['error_atlas_'+name+'.png' for name in views],
 'native_blender_scene':native.name,
 'measurement_contract':'region labels by closest MPFB rest-bone segment, not true 1:1 anatomical landmarks',
 'action':'Landmark-specific body/face/hand/hip/foot registration BEFORE attempting rig weight transfer; preserve original CC0 sculpt topology, UVs and rights',
 'limits':['Numerical surface distances and bone proxies only; not true anatomical landmark correspondence',
           'No physiology, external reproductive anatomy, pose contact, FACS or cinematic quality acceptance',
           'A green research run must still return HOLD, and old torn rigs remain quarantined']
}
(args.out/'registration_region_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print('R014_REGISTRATION_REGION_ATLAS',json.dumps({'sex':args.sex,'status':receipt['status'],
 'global_p95_m':receipt['global_registration']['p95_m'],
 'top_regions':priorities[:5],
 'target_vertices':len(tgt)},sort_keys=True),flush=True)
