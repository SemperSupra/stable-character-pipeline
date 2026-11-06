"""Independent Blender 4.5 30-joint GLB ankle-to-plan observable."""
import bpy,hashlib,importlib.util,json,math,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from target_residual import screen,FEET

def main():
    if '--' not in sys.argv:raise SystemExit('blender -- source.glb pinned_footpaths.py report.json')
    args=sys.argv[sys.argv.index('--')+1:]
    if len(args)!=3:raise SystemExit('source.glb pinned_footpaths.py report.json')
    glb,plan,out=map(Path,args)
    spec=importlib.util.spec_from_file_location('pinned_shetland_footpaths',plan)
    if spec is None or spec.loader is None:raise ValueError('invalid frozen source plan')
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    if module.CYCLE_FRAMES!=48 or module.STRIDE_M!=.16 or module.ANKLE_BASE_Z_M!=.252:
        raise ValueError('source plan changed, no silently renewed acceptance')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    arms=[x for x in bpy.context.scene.objects if x.type=='ARMATURE']
    if len(arms)!=1 or len(arms[0].data.bones)!=30:
        raise ValueError('requires exported single 30-joint pony')
    arm=arms[0]
    samples={f:[] for f in FEET}
    for frame in range(1,49):
        bpy.context.scene.frame_set(frame)
        evaluated=arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
        for foot in FEET:
            tail=evaluated.pose.bones.get(foot+'_lower')
            if tail is None:raise ValueError('missing actual lower bone '+foot)
            p=evaluated.matrix_world@Vector(tail.tail)
            q=module.target(frame,foot)
            if q.frame!=frame or q.foot!=foot:raise ValueError('wrong source gait clock')
            samples[foot].append({'frame':frame,
                'actual_world_lower_tail_xyz':[float(v) for v in p],
                'planned_world_ankle_xyz':[q.ankle_x,q.ankle_y,q.ankle_z],
                'source_state':q.state})
    r=screen(samples)
    r['glb_name']=glb.name
    r['glb_sha256']=hashlib.sha256(glb.read_bytes()).hexdigest()
    r['source_plan_sha256']=hashlib.sha256(plan.read_bytes()).hexdigest()
    r['blender_version']=bpy.app.version_string
    r['samples']=samples
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print('ACTUAL_EXPORTED_IK_ANKLE_TARGET_RESIDUAL_NOT_FORCE',r['total_front_frames_over_20mm'])
main()
