import bpy

def version():
    return bpy.app.version_string

import math

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
