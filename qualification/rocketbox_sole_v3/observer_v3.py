#!/usr/bin/env python3
"""Actual MIT V3 native 72f foot-sole/ground observer; NOT gait approval."""
import hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'rocketbox_gait_v3'))
from gait_v3 import find_native_armatures, author_source_keys, compose_park, SOURCE_BLEND_SHA, ACTORS
ROOTS=tuple(ACTORS)
V3_OWNER_HEAD='2a8a9a168b60b742c0c0bcb8be40cd46cf3ab45c'
SIDES=('L','R')
FRAMES=72
def finite(v): return type(v) in (int,float) and math.isfinite(v)
def metrics(samples,ground):
    if not finite(ground):raise ValueError('GROUND_NONFINITE')
    if len(samples)!=FRAMES:raise ValueError('FRAME_COUNT_NOT_72')
    result={}
    for root in ROOTS:
        result[root]={}
        for side in SIDES:
            key=root+':'+side
            a=[x[key] for x in samples]
            if any(not all(finite(s.get(k)) for k in ('min_z','x','y')) for s in a):
                raise ValueError('NONFINITE_FOOT_REGION')
            near=[-.07<=s['min_z']-ground<=.035 for s in a]
            deltas=[]
            for i in range(1,FRAMES):
                if near[i-1] and near[i]:
                    deltas.append({'from':i-1,'to':i,'distance_m':round(math.hypot(a[i]['x']-a[i-1]['x'],a[i]['y']-a[i-1]['y']),6)})
            maximal=max((d['distance_m'] for d in deltas),default=None)
            result[root][side]={'near_ground_frames':sum(near),'consecutive_near_ground_pairs':len(deltas),
                'max_near_ground_delta_m_per_frame':maximal,
                'over_8cm_pairs':sum(d['distance_m']>.08 for d in deltas),
                'min_above_path_m':round(min(s['min_z']-ground for s in a),7),
                'penetrating_over_2cm_frames':sum(s['min_z']-ground<-.02 for s in a),
                'classification':('OBSERVED_GROUND_PENETRATION' if min(s['min_z']-ground for s in a)<-.02 else
                    'UNKNOWN_NO_CONSECUTIVE_NEAR_GROUND_SAMPLES' if maximal is None else
                    'OBSERVED_POSSIBLE_SLIDE' if maximal>.08 else 'NO_LARGE_SLIDE_IN_OBSERVED_NEAR_GROUND_WINDOWS_NOT_CONTACT_PASS'),
                'observed_pairs':deltas}
    return result
def native(blend,out,want):
    import bpy
    from mathutils import Vector
    if hashlib.sha256(blend.read_bytes()).hexdigest()!=want:
        raise RuntimeError('ORIGINAL_BLEND_SHA_MISMATCH')
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene=bpy.context.scene
    if (scene.frame_start,scene.frame_end,scene.render.fps)!=(0,71,12):
        raise RuntimeError('SOURCE_FRAME_CLOCK_MISMATCH')
    # Original source scene has V1 local-X swing; independently author exact
    # measured local-Z V3 keys before geometry observation. No self-issued stance.
    actors=find_native_armatures(bpy)
    source_root_trajectory=author_source_keys(bpy,actors)
    compose_park(bpy)
    ground=bpy.data.objects.get('OriginalPark_Walkway')
    if ground is None or ground.type!='MESH':raise RuntimeError('SOURCE_GROUND_ABSENT')
    top=max(float((ground.matrix_world@Vector(v)).z) for v in ground.bound_box)
    if not finite(top):raise RuntimeError('GROUND_NONFINITE')
    parts={}
    for rootname in ROOTS:
        root=bpy.data.objects.get(rootname)
        if root is None:raise RuntimeError('SOURCE_ACTOR_ABSENT:'+rootname)
        arm=[o for o in bpy.data.objects if o.type=='ARMATURE' and
             (o.parent==root or (o.parent and o.parent.parent==root))]
        if len(arm)!=1:raise RuntimeError('SOURCE_ARMATURE_AMBIGUOUS:'+rootname)
        meshes=[o for o in bpy.data.objects if o.type=='MESH' and
                any(m.type=='ARMATURE' and m.object==arm[0] for m in o.modifiers)]
        if len(meshes)!=1:raise RuntimeError('SOURCE_SKIN_AMBIGUOUS:'+rootname)
        mesh=meshes[0]
        names={g.name:g.index for g in mesh.vertex_groups}
        regions={}
        for side in SIDES:
            group_names=(f'Bip01 {side} Foot',f'Bip01 {side} Toe0')
            if not all(n in names for n in group_names):
                raise RuntimeError('SOURCE_FOOT_VERTEX_GROUP_MISSING:'+rootname+':'+side)
            ids={names[n] for n in group_names}
            indices=[v.index for v in mesh.data.vertices if
                     sum(g.weight for g in v.groups if g.group in ids)>=.5]
            if len(indices)<5:
                raise RuntimeError('SOURCE_WEIGHTED_FOOT_REGION_UNOBSERVABLE:'+rootname+':'+side)
            regions[side]=indices
        parts[rootname]=(mesh,regions)
    rows=[]
    for frame in range(FRAMES):
        scene.frame_set(frame);bpy.context.view_layer.update()
        deps=bpy.context.evaluated_depsgraph_get()
        row={}
        for rootname,(mesh,regions) in parts.items():
            obj=mesh.evaluated_get(deps)
            evaluated=obj.to_mesh()
            try:
                for side,indices in regions.items():
                    points=[obj.matrix_world @ evaluated.vertices[i].co for i in indices]
                    row[rootname+':'+side]={'min_z':min(float(v.z) for v in points),
                        'x':sum(float(v.x) for v in points)/len(points),
                        'y':sum(float(v.y) for v in points)/len(points)}
            finally:obj.to_mesh_clear()
        rows.append(row)
    result=metrics(rows,top)
    receipt={'schema':'scp.r009.mit_native_v3_weighted_foot_observation.v1',
      'source_v3_head':V3_OWNER_HEAD,
      'source_v3_root_world_x_all72':source_root_trajectory,
      'status':'ACTUAL_NATIVE_ALL72_FOOT_REGION_MEASUREMENTS_ONLY',
      'source_blend_sha256':want,'fps':12,'frames':FRAMES,
      'ground_top_z_m':top,'ground_source':'V3_PROJECT_AUTHORED_BLENDER_PATH_EVALUATED',
      'threshold_weight':.5,
      'near_ground_lower_m':-.07,'near_ground_upper_m':.035,
      'slide_screen_threshold_m_per_frame':.08,
      'measured_regions':result,
      'physical_contact':'UNKNOWN','rest_basis_calibrated':False,
      'joint_rom':'UNKNOWN','biological_gait':'UNKNOWN',
      'independent_pixel_visibility':'NOT_RUN','product_accepted':False}
    out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'status':receipt['status'],'summary':{
        a:{s:{k:v for k,v in d.items() if k!='observed_pairs'} for s,d in b.items()}
        for a,b in result.items()},'product_accepted':False},sort_keys=True))
if __name__=='__main__':
    if '--' not in sys.argv:raise SystemExit('USAGE: blender -b --python observer.py -- original.blend out.json SHA256')
    args=sys.argv[sys.argv.index('--')+1:]
    if len(args)!=3:raise SystemExit('USAGE original.blend receipt.json SHA256')
    native(Path(args[0]).resolve(),Path(args[1]).resolve(),args[2])
