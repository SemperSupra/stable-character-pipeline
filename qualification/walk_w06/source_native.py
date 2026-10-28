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
