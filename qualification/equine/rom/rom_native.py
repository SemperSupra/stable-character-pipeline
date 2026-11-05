"""Native Blender imported exported-GLB 48f actual world-space knee/hock screen."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from rom_metrics import evaluate,FEET

def main():
    if "--" not in sys.argv:raise SystemExit("blender -- -source.glb out.json")
    a=sys.argv[sys.argv.index("--")+1:]
    if len(a)!=2:raise SystemExit("source.glb receipt.json")
    source,out=map(Path,a)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    arms=[x for x in bpy.context.scene.objects if x.type=="ARMATURE"]
    if len(arms)!=1:raise RuntimeError("single GLB source rig expected")
    arm=arms[0]
    all_names={bone.name for bone in arm.data.bones}
    observations={f:[] for f in FEET}
    for frame in range(1,49):
        bpy.context.scene.frame_set(frame)
        dg=bpy.context.evaluated_depsgraph_get()
        ar=arm.evaluated_get(dg)
        for foot in FEET:
            upper=ar.pose.bones.get(foot+"_upper")
            lower=ar.pose.bones.get(foot+"_lower")
            if upper is None or lower is None:raise RuntimeError("missing source upper/lower limb")
            def v(point):
                p=ar.matrix_world@Vector(point)
                return tuple(float(x) for x in p)
            observations[foot].append({"frame":frame,
                "proximal":v(upper.head),"joint":v(upper.tail),
                "distal":v(lower.tail)})
    result=evaluate(observations,all_names)
    result["native_blender"]=bpy.app.version_string
    result["source_glb"]=source.name
    result["sources"]=list(sorted(all_names))
    result["measured_trajectories"]=observations
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"technical":"MEASURED_REAL_48F_GLTF_POSE",
        "science":result["scientific_verdict"],"failures":result["failure_codes"]},sort_keys=True))
main()
