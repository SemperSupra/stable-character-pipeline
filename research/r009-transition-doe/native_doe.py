"""Real original Blender curve experiment, no protected or human rig data."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import bpy
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent/"r009-paired-envelope"))
from profiles import point
from paired_envelope import SCHEMA, MARKERS, schedule
WINDOWS=[[40,80]]
def empty(name,parent=None,loc=(0,0,0)):
    ob=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(ob);ob.parent=parent;ob.location=loc
    return ob
def boot(name,parent,y):
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata([(-.06,-.04,0),(.06,-.04,0),(.06,.04,0),(-.06,.04,0)],[],[(0,1,2,3)])
    mesh.update();ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
    ob.parent=parent;ob.location=(0,y,0);return ob
def curves(ob):
    ad=ob.animation_data
    out=[]
    for layer in ad.action.layers:
        for strip in layer.strips:
            bag=strip.channelbag(ad.action_slot)
            if bag:out.extend(bag.fcurves)
    if len(out)!=3 or {fc.array_index for fc in out}!={0,1,2}:raise ValueError("ACTION_XYZ")
    return out
def expected_frames(half):
    return [0.]+[i/4 for i in range((60-half)*4,(60+half)*4+1)]+[359.]
def build(path,kind,half):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc=bpy.context.scene;sc.render.fps=60;sc.render.fps_base=1;sc.frame_start=0;sc.frame_end=359
    sc["source_class"]="ORIGINAL_SYNTHETIC";sc["profile"]=kind;sc["half"]=half
    frames=expected_frames(half)
    for actor,y in (("a",0),("b",2)):
        root=empty(actor+"_root",loc=(0,y,0))
        for m in MARKERS[1:]:empty(actor+"_"+m,root,(0,0,1 if m in ("pelvis","torso") else .4))
        left=boot(actor+"_L",root,-.1);boot(actor+"_R",root,.1)
        for frame in frames:
            shift=point(kind,half,frame)[0] if kind!="reference" and actor=="a" else 0.
            root.location.x=shift;left.location.x=-shift
            root.keyframe_insert("location",frame=frame);left.keyframe_insert("location",frame=frame)
        for ob,sign in ((root,1),(left,-1)):
            for fc in curves(ob):
                keys=list(fc.keyframe_points)
                if len(keys)!=len(frames):raise ValueError("KEY_COUNT")
                for i,k in enumerate(keys):
                    if kind in ("linear","reference"):
                        k.interpolation="LINEAR"
                        continue
                    k.interpolation="BEZIER"
                    k.handle_left_type=k.handle_right_type="FREE"
                    x,yv=float(k.co.x),float(k.co.y)
                    slope=sign*point(kind,half,x)[1] if actor=="a" and fc.array_index==0 else 0.
                    dl=(x-frames[i-1])/3 if i else 1/3
                    dr=(frames[i+1]-x)/3 if i+1<len(frames) else 1/3
                    k.handle_left=(x-dl,yv-slope*dl);k.handle_right=(x+dr,yv+slope*dr)
                fc.update()
    sc.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(Path(path).resolve()))
def sample(path,out,kind,half):
    sc=bpy.context.scene
    if Path(bpy.data.filepath).resolve()!=Path(path).resolve() or sc.get("profile")!=kind or sc.get("half")!=half:
        raise ValueError("REOPEN_IDENTITY")
    if (sc.render.fps,sc.render.fps_base,sc.frame_start,sc.frame_end)!=(60,1.,0,359) or sc.get("source_class")!="ORIGINAL_SYNTHETIC":
        raise ValueError("SCENE_CLOCK")
    frames=expected_frames(half)
    mode="LINEAR" if kind in ("linear","reference") else "BEZIER"
    for actor in ("a","b"):
        for name in ("root","L"):
            for fc in curves(bpy.data.objects[actor+"_"+name]):
                if [float(k.co.x) for k in fc.keyframe_points]!=frames or any(k.interpolation!=mode for k in fc.keyframe_points):
                    raise ValueError("REOPEN_CURVES")
    rows=[]
    for tick in schedule(WINDOWS):
        sc.frame_set(tick//32,subframe=(tick%32)/32);dg=bpy.context.evaluated_depsgraph_get()
        actors={}
        for actor in ("a","b"):
            markers={m:list(bpy.data.objects[actor+"_"+m].evaluated_get(dg).matrix_world.translation) for m in MARKERS}
            feet={}
            for side in ("L","R"):
                ob=bpy.data.objects[actor+"_"+side].evaluated_get(dg);mesh=ob.to_mesh()
                try:feet[side]={str(v.index):list(ob.matrix_world@v.co) for v in mesh.vertices}
                finally:ob.to_mesh_clear()
            actors[actor]=dict(markers=markers,feet=feet)
        rows.append(dict(tick=tick,actors=actors))
    with open(out,"x") as f:json.dump(dict(schema=SCHEMA,source_class="ORIGINAL_SYNTHETIC",
        scene_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),fps=60,subdiv=32,
        physical_contact_accepted=False,protected_likeness_used=False,rows=rows),f,allow_nan=False)
p=argparse.ArgumentParser()
p.add_argument("--stage",choices=("build","sample"),required=True)
p.add_argument("--kind",choices=("reference","linear","cubic","quintic"),required=True)
p.add_argument("--half",type=int,choices=(10,20),required=True)
p.add_argument("--scene",required=True);p.add_argument("--out")
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
if a.stage=="build":build(a.scene,a.kind,a.half)
else:sample(a.scene,a.out,a.kind,a.half)
