#!/usr/bin/env python3
"""Original synthetic Shetland procedural v2 proof, NOT the local v1 GLB source.
Runs inside Blender 4.5.15 to produce genuine rigged GLBs, editable .blend files and stills.
Reference photographs/video, protected people and vendor meshes are not uploaded.
"""
import bpy, math, random, json, hashlib, sys, os
from mathutils import Vector
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ik_walk import animate_ik_walk
from body_surface import create_body_surface
from equine_sculpt import create_equine_sculpt

OUT=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv else Path('/tmp/shetland-results')
OUT.mkdir(parents=True,exist_ok=True)
SEED=20261105
COATS={
 'black': ((.021,.023,.029,1),(.012,.013,.018,1),(.19,.19,.2,1),(.90,.28,.54,1)),
 'pinto': ((.41,.14,.07,1),(.84,.70,.49,1),(.22,.18,.16,1),(.09,.08,.07,1)),
 'white': ((.82,.8,.75,1),(.88,.85,.78,1),(.27,.25,.23,1),None),
}

def material(name,color,rough=.9):
 m=bpy.data.materials.new(name);m.diffuse_color=color;m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=color;p.inputs['Roughness'].default_value=rough
 return m

def ellipsoid(name,position,radii,mat):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=14,location=position)
 o=bpy.context.object;o.name=name;o.scale=radii
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if mat:o.data.materials.append(mat)
 for f in o.data.polygons:f.use_smooth=True
 return o

def rigged(obj, arm, bone, alt=None, ratio=0):
 g=obj.vertex_groups.new(name=bone)
 g.add(list(range(len(obj.data.vertices))),1-ratio,'REPLACE')
 if alt and ratio:
  gg=obj.vertex_groups.new(name=alt);gg.add(list(range(len(obj.data.vertices))),ratio,'REPLACE')
 obj.parent=arm;mod=obj.modifiers.new('Armature Skin','ARMATURE');mod.object=arm
 return obj

def new_armature():
 data=bpy.data.armatures.new('Shetland26');arm=bpy.data.objects.new('PonyRig26',data);bpy.context.collection.objects.link(arm)
 bpy.context.view_layer.objects.active=arm;arm.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
 specs=[
 ('root',None,(-.09,0,.73),(-.09,0,.84)),
 ('body','root',(-.4,0,.8),(.38,0,.8)),
 ('neck','body',(.34,0,.83),(.65,0,1.13)),
 ('head','neck',(.65,0,1.13),(.96,0,.87)),
 ('jaw','head',(.82,0,.91),(.97,0,.82)),
 ('ear_L','head',(.73,-.13,1.20),(.75,-.14,1.37)),
 ('ear_R','head',(.73,.13,1.20),(.75,.14,1.37)),
 ('tail_1','body',(-.57,0,.88),(-.73,0,.76)),
 ('tail_2','tail_1',(-.73,0,.76),(-.85,0,.55)),
 ('tail_3','tail_2',(-.85,0,.55),(-.89,0,.35)),
 ]
 for side in ('L','R'):
  y=-.20 if side=='L' else .20
  for prefix,x in (('front',.40),('hind',-.48)):
   h=.81 if prefix=='front' else .78
   specs += [
    (f'{prefix}_{side}_upper','body',(x,y,h),(x-.015,y,.47)),
    (f'{prefix}_{side}_lower',f'{prefix}_{side}_upper',(x-.015,y,.47),(x+.012,y,.26)),
    (f'{prefix}_{side}_fetlock',f'{prefix}_{side}_lower',(x+.012,y,.26),(x+.03,y,.12)),
    (f'{prefix}_{side}_hoof',f'{prefix}_{side}_fetlock',(x+.03,y,.12),(x+.04,y,.035)),
   ]
 for name,parent,head,tail in specs:
  b=data.edit_bones.new(name);b.head=head;b.tail=tail
  if parent:b.parent=data.edit_bones[parent];b.use_connect=False
 bpy.ops.object.mode_set(mode='OBJECT');arm.select_set(False)
 assert len(arm.data.bones)==26,len(arm.data.bones)
 return arm

def groom_mesh(name,anchors,mat,arm):
 v=[];f=[];groups=[]
 for p,d,length,width,bone in anchors:
  p=Vector(p);d=Vector(d).normalized();side=d.cross(Vector((0,1,0)))
  if side.length<.01:side=Vector((1,0,0))
  side.normalize();q=p+d*length
  a=len(v);v.extend([p-side*width,p+side*width,q-side*width*.10,q+side*width*.10])
  f.extend([(a,a+1,a+2),(a+1,a+3,a+2)])
  groups.append((bone,range(a,a+4)))
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(v,[],f);mesh.update()
 obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);obj.data.materials.append(mat)
 indexes={}
 for bone,ids in groups:indexes.setdefault(bone,[]).extend(ids)
 for bone,ids in indexes.items():obj.vertex_groups.new(name=bone).add(ids,1,'REPLACE')
 obj.parent=arm;mod=obj.modifiers.new('Deform with rig','ARMATURE');mod.object=arm
 return obj

def build_one(coat):
 bpy.ops.wm.read_factory_settings(use_empty=True)
 rng=random.Random(SEED)
 body_color,hair_color,hoof_color,halter_color=COATS[coat]
 body=material('coat_'+coat,body_color);hair=material('mane_tail_'+coat,hair_color);hoof=material('hoof',hoof_color)
 nose=material('muzzle',(body_color[0]*.7,body_color[1]*.7,body_color[2]*.7,1))
 eye=material('eyes',(.015,.011,.01,1),.14);pink=material('halter',halter_color) if halter_color else None
 if coat=='pinto':white=material('pinto_patches',(.86,.84,.76,1))
 arm=new_armature()
 create_body_surface(arm,body,white if coat=='pinto' else None)
 create_equine_sculpt(arm,body,body)
 for side in ('L','R'):
  sign=-1 if side=='L' else 1;y=sign*.205
  for prefix,x in (('front',.40),('hind',-.48)):
   # The continuous skinned limb mesh replaces disconnected rounded cuffs.
   bpy.ops.mesh.primitive_cone_add(vertices=24,radius1=.11,radius2=.085,depth=.115,location=(x+.025,y,.065))
   o=bpy.context.object;o.name=f'{prefix}_{side}_hoof';o.data.materials.append(hoof);rigged(o,arm,o.name)
  for name,loc,sc,mat,bone in [
   ('ear',(.72,sign*.14,1.32),(.043,.033,.13),body,'ear_'+side),
   ('eye',(.795,sign*.147,1.145),(.035,.015,.031),eye,'head'),
   ('nostril',(1.137,sign*.094,.86),(.032,.013,.023),eye,'head'),
   ('mouth',(1.137,sign*.085,.798),(.044,.010,.008),nose,'jaw'),
  ]:
   rigged(ellipsoid(name+'_'+side,loc,sc,mat),arm,bone)
 for i,(p,sc,bone) in enumerate([
  ((-.68,0,.79),(.095,.10,.19),'tail_1'),
  ((-.78,0,.60),(.085,.10,.19),'tail_2'),
  ((-.88,0,.43),(.07,.09,.15),'tail_3')]):
  rigged(ellipsoid('tail_volume_'+str(i),p,sc,hair),arm,bone)
 # Pinto markings now use material islands on the unified body surface.
 anchors=[]
 for i in range(1100):
  t=rng.random()*math.tau;u=rng.uniform(-1,1);theta=math.acos(u)
  p=(-.05+.596*math.sin(theta)*math.cos(t),.309*math.sin(theta)*math.sin(t),.80+.319*math.cos(theta))
  anchors.append((p,(rng.uniform(-.12,.13),rng.uniform(-.17,.17),.8+rng.random()*.4),.022+rng.random()*.045,.004,'body'))
 for i in range(160):
  x=.36+i/160*.45;y=rng.uniform(-.14,.14);z=1.08+(x-.36)*.20
  anchors.append(((x,y,z),(rng.uniform(-.22,.1),rng.choice((-1,1))*.32,.35),rng.uniform(.14,.32),.009,'neck' if x<.66 else 'head'))
 for i in range(100):
  anchors.append(((.73+rng.uniform(-.05,.15),rng.uniform(-.13,.13),1.27),(.75,rng.uniform(-.28,.28),-.22),rng.uniform(.14,.28),.008,'head'))
 for i in range(160):
  z=rng.uniform(.35,.82)
  anchors.append(((-.70,rng.uniform(-.095,.095),z),(-.35,rng.uniform(-.15,.15),-.45),rng.uniform(.1,.32),.010,'tail_2' if z>.55 else 'tail_3'))
 groom_mesh('geometric_coat_mane_tail',anchors,hair,arm)
 if pink:
  for nm,pos,sc in [('noseband',(.97,0,.93),(.019,.162,.027)),('cheekstrap',(.81,-.164,1.02),(.023,.019,.14)),('cheekstrap2',(.81,.164,1.02),(.023,.019,.14))]:
   rigged(ellipsoid(nm,pos,sc,pink),arm,'head')
 animate_ik_walk(arm,OUT/f'ik_plan_{coat}.json')
 bpy.context.scene.frame_set(1)
 bpy.ops.object.select_all(action='DESELECT')
 for o in bpy.context.scene.objects:
  if o.type in {'MESH','ARMATURE'}:o.select_set(True)
 bpy.context.view_layer.objects.active=arm
 out=OUT/f'shetland_{coat}_ghcr'
 bpy.ops.export_scene.gltf(filepath=str(out)+'.glb',export_format='GLB',use_selection=True,export_animations=True,export_skins=True)
 bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.015))
 ground=bpy.context.object;ground.name='ground';ground.data.materials.append(material('sand',(.63,.59,.51,1)))
 def track(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
 bpy.ops.object.camera_add(location=(2.55,-3.40,1.71))
 cam=bpy.context.object;track(cam,(.06,0,.73));cam.data.type='ORTHO';cam.data.ortho_scale=2.7;bpy.context.scene.camera=cam
 for i,loc in enumerate([(1,-2,3),(-1.5,1,2.2)]):
  bpy.ops.object.light_add(type='AREA',location=loc)
  light=bpy.context.object;light.data.energy=550 if i==0 else 280;light.data.shape='DISK';light.data.size=3.0;track(light,(0,0,.7))
 sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=16
 sc.render.resolution_x=640;sc.render.resolution_y=420;sc.render.resolution_percentage=100
 sc.render.image_settings.file_format='PNG';sc.render.filepath=str(out)+'.png'
 bpy.ops.render.render(write_still=True)
 bpy.ops.wm.save_as_mainfile(filepath=str(out)+'.blend')
 results={}
 for suffix in ('.glb','.blend','.png'):
  p=Path(str(out)+suffix);assert p.stat().st_size>512,(p,p.stat().st_size)
  results[p.name]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 return results

receipt={'tool':'native_blender_shetland_ghcr','reference':'public-safe synthetic pony derivative; not local v1','blender':bpy.app.version_string,'coat_results':{}}
selected_coats=os.environ.get("SCP_COATS","black,pinto,white").split(",")
if not selected_coats or any(x not in COATS for x in selected_coats) or len(set(selected_coats))!=len(selected_coats):
 raise ValueError("invalid SC PONY coat subset")
for c in selected_coats:receipt['coat_results'][c]=build_one(c)
p=OUT/'manifest.json';p.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'VERDICT':'NATIVE_SYNTHETIC_THREE_COAT_PASS','manifest':str(p)},sort_keys=True))
