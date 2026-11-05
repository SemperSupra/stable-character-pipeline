"""Blender-native evaluated rigid+skinned hoof mesh probe for *one* source-original pony."""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import FEET, evaluate

def main():
    args=sys.argv[sys.argv.index("--")+1:]
    source=Path(args[0]);out=Path(args[1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    meshes=[o for o in bpy.data.objects if o.type=="MESH"]
    samples={}
    for exact in FEET:
        matches=[o for o in meshes if o.name==exact or o.name.startswith(exact+".")]
        if len(matches)!=1:
            raise RuntimeError(f"missing/ambiguous hoof object {exact}, matches={len(matches)}")
        obj=matches[0]
        points=[]
        scene=bpy.context.scene
        for frame in range(1,49):
            scene.frame_set(frame)
            dg=bpy.context.evaluated_depsgraph_get()
            evaluated=obj.evaluated_get(dg)
            mesh=evaluated.to_mesh()
            try:
                if not mesh.vertices:
                    raise RuntimeError("empty hoof mesh")
                verts=[evaluated.matrix_world @ v.co for v in mesh.vertices]
                points.append({"frame":frame,"x":sum(v.x for v in verts)/len(verts),
                    "y":sum(v.y for v in verts)/len(verts),
                    "min_z":min(v.z for v in verts)})
            finally:
                evaluated.to_mesh_clear()
        samples[exact]=points
    report=evaluate(samples)
    report["evaluated_hoof_trajectories"]=samples
    report["blender"]=bpy.app.version_string
    report["source_model"]=source.name
    report["animation_source"]="native evaluated 48 frames, source-art 26-joint procedural gait"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"FOOT_SCIENCE":report["scientific_verdict"],
        "skate_pairs":report["total_skate_pairs_over_threshold"],
        "max_slide_m":report["maximum_near_ground_displacement_m"],
        "max_penetration_m":report["maximum_ground_penetration_m"]}))
main()
