import bpy

def version():
    return bpy.app.version_string

import math

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

from pathlib import Path
COLORS={"cobalt-automaton":("#297a99","#f4b35e"),"marigold-explorer":("#d78b44","#7653a7")}

def make_piece(name,color,order):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=1)
    obj=bpy.context.object
    obj.name=name
    return (obj,color,order)

def pose_piece(piece,frame,x,y,width,height,angle=0):
    obj=piece[0]
    obj.location=(x,y,0)
    obj.scale=(width/2,height/2,.08)
    obj.rotation_euler=(0,0,angle)
    for item in ("location","scale","rotation_euler"):
        obj.keyframe_insert(data_path=item,frame=frame)

def between(piece,frame,a,b,width):
    dx=b[0]-a[0];dy=b[1]-a[1]
    pose_piece(piece,frame,(a[0]+b[0])/2,(a[1]+b[1])/2,
               width,math.hypot(dx,dy)+.06,math.atan2(-dx,dy))

def character(actor):
    aid=actor["id"];base,accent=COLORS[aid]
    pieces={}
    for side in ("left","right"):
        for name,color,order in (("thigh",base,1),("shin",base,1),
                                 ("foot",accent,2),("upperarm",base,2),
                                 ("forearm",base,4)):
            key=name+"_"+side
            pieces[key]=make_piece(aid+"_"+key,color,order)
    for name,color,order in (("torso",base,3),("head",base,5),
                             ("visor",accent,6),("eye","#213343",7),
                             ("hat",accent,8)):
        pieces[name]=make_piece(aid+"_"+name,color,order)
    return pieces

def animate(p,actor,pose,frame):
    joints=pose["joints"];direction=actor["facing"]
    for side in ("left","right"):
        between(p["thigh_"+side],frame,joints["hip_"+side],joints["knee_"+side],.18)
        between(p["shin_"+side],frame,joints["knee_"+side],joints["ankle_"+side],.16)
        x,y=joints["ankle_"+side]
        pose_piece(p["foot_"+side],frame,x+direction*.07,y-.03,.32,.13)
        between(p["upperarm_"+side],frame,joints["shoulder_"+side],joints["elbow_"+side],.14)
        between(p["forearm_"+side],frame,joints["elbow_"+side],joints["wrist_"+side],.13)
