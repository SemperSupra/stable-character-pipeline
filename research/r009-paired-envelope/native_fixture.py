"""Real Blender saved/reopened original marker/mesh counterexample, not human rig."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import bpy

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from paired_envelope import SCHEMA, MARKERS, schedule

WINDOWS=[[50,70]]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def empty(name,parent=None,loc=(0,0,0)):
    ob=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(ob)
    ob.parent=parent;ob.location=loc
    return ob

def boot(name,parent,y):
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata([(-.06,-.04,0),(.06,-.04,0),(.06,.04,0),(-.06,.04,0)],[],[(0,1,2,3)])
    mesh.update()
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
    ob.parent=parent;ob.location=(0,y,0)
    return ob

def build(path,candidate):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc=bpy.context.scene;sc.render.fps=60;sc.render.fps_base=1;sc.frame_start=0;sc.frame_end=359
    bpy.context.preferences.edit.keyframe_new_interpolation_type="LINEAR"
    sc["source_class"]="ORIGINAL_SYNTHETIC"
    for a,y in (("a",0),("b",2)):
        root=empty(a+"_root",loc=(0,y,0))
        for name in MARKERS[1:]:
            empty(a+"_"+name,root,(0,0,1 if name in ("pelvis","torso") else .4))
        left=boot(a+"_L",root,-.1);boot(a+"_R",root,.1)
        # Both variants have same stationary left material over the clip.
        # The candidate moves the root and opposite foot while compensating left.
        for frame in (0,50,60,70,359):
            delta=.03 if candidate and a=="a" and frame==60 else 0.
            root.location.x=delta;left.location.x=-delta
            root.keyframe_insert("location",frame=frame);left.keyframe_insert("location",frame=frame)
    sc.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(path).resolve()))

def sample(path,out):
    sc=bpy.context.scene
    if (sc.render.fps,sc.render.fps_base,sc.frame_start,sc.frame_end)!=(60,1.,0,359) or sc.get("source_class")!="ORIGINAL_SYNTHETIC":
        raise ValueError("unexpected native source")
    if Path(bpy.data.filepath).resolve()!=Path(path).resolve():
        raise ValueError("not reopened requested source")
    rows=[]
    for tick in schedule(WINDOWS):
        sc.frame_set(tick//32,subframe=(tick%32)/32)
        dg=bpy.context.evaluated_depsgraph_get()
        actors={}
        for a in ("a","b"):
            markers={m:list(bpy.data.objects[a+"_"+m].evaluated_get(dg).matrix_world.translation) for m in MARKERS}
            feet={}
            for side in ("L","R"):
                ob=bpy.data.objects[a+"_"+side].evaluated_get(dg)
                mesh=ob.to_mesh()
                try:feet[side]={str(v.index):list(ob.matrix_world@v.co) for v in mesh.vertices}
                finally:ob.to_mesh_clear()
            actors[a]=dict(markers=markers,feet=feet)
        rows.append(dict(tick=tick,actors=actors))
    with open(out,"x") as f:
        json.dump(dict(schema=SCHEMA,source_class="ORIGINAL_SYNTHETIC",scene_sha256=sha(path),
            fps=60,subdiv=32,physical_contact_accepted=False,protected_likeness_used=False,rows=rows),f,allow_nan=False)

p=argparse.ArgumentParser()
p.add_argument("--stage",choices=["reference","candidate","sample"],required=True)
p.add_argument("--scene",required=True);p.add_argument("--out")
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
if a.stage=="sample":sample(a.scene,a.out)
else:build(a.scene,a.stage=="candidate")
