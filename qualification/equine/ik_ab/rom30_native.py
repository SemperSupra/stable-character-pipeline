"""Headless Blender 4.5 source-independent real GLB 30-joint ROM observer."""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from rom30_metrics import evaluate, FEET, LINKS

def main():
    if '--' not in sys.argv:raise SystemExit('blender -- source.glb receipt.json')
    a=sys.argv[sys.argv.index('--')+1:]
    if len(a)!=2:raise SystemExit('source.glb receipt.json')
    source,out=map(Path,a)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    arms=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
    if len(arms)!=1:raise ValueError('one native GLB armature required')
    arm=arms[0]
    bones={b.name for b in arm.data.bones}
    measured={foot:[] for foot in FEET}
    for frame in range(1,49):
        bpy.context.scene.frame_set(frame)
        dg=bpy.context.evaluated_depsgraph_get()
        actual=arm.evaluated_get(dg)
        for foot in FEET:
            seg=[]
            for name in LINKS[foot]:
                pb=actual.pose.bones.get(name)
                if pb is None:raise ValueError('missing animated source bone '+name)
                def world(v):return [float(q) for q in (actual.matrix_world @ Vector(v))]
                seg.append({'name':name,'head':world(pb.head),'tail':world(pb.tail)})
            measured[foot].append({'frame':frame,'links':seg})
    report=evaluate(measured,bones)
    report['source_glb']=source.name
    report['blender_version']=bpy.app.version_string
    report['measured_trajectories']=measured
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print('NATIVE_THREE_SEGMENT_30J',report['scientific_verdict'],report['failure_codes'])
main()
