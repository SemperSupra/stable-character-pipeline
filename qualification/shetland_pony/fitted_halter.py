"""Parametric, head-attached Shetland halter. All positions in pony rest coordinates.
Public-original engineering candidate, not a certified fit for live animals.
"""
import math

# Real continuous strap strips, not scaled spherical proxies. Offsets in metres.
NOSE_X=1.055
NOSE_Z=.879
NOSE_RY=.111
NOSE_RZ=.080
STRAP_WIDTH=.023
HALTER_CLEARANCE=.008

def nose_loop(steps=64):
    if steps<24 or steps>256: raise ValueError("invalid ring resolution")
    return [(NOSE_X,NOSE_RY*math.cos(2*math.pi*i/steps),
             NOSE_Z+NOSE_RZ*math.sin(2*math.pi*i/steps)) for i in range(steps)]

def cheek_path(side):
    if side not in ("L","R"): raise ValueError("invalid side")
    s=-1 if side=="L" else 1
    return [(1.051,s*.107,.886),(.982,s*.111,.950),(.899,s*.140,1.019),
            (.800,s*.158,1.100),(.724,s*.151,1.174)]

def crown_loop(steps=32):
    # Over the poll, rather than through the head; arched around its width.
    if steps<12: raise ValueError("invalid crown samples")
    return [(.724,.154*math.cos(math.pi*i/(steps-1)),
             1.172+.112*math.sin(math.pi*i/(steps-1))) for i in range(steps)]

def throat_loop(steps=24):
    if steps<12: raise ValueError("invalid throat samples")
    return [(.752,.154*math.cos(math.pi*i/(steps-1)),
             1.130-.172*math.sin(math.pi*i/(steps-1))) for i in range(steps)]

def strap_surface(points, width=STRAP_WIDTH, closed=False):
    """Generate double-sided ribbon quad topology with oriented local tangents."""
    if len(points)<3 or not 0<width<.08: raise ValueError("invalid strap")
    vertices=[];faces=[]
    for i,p in enumerate(points):
        a=points[(i-1)%len(points)] if closed or i>0 else points[0]
        b=points[(i+1)%len(points)] if closed or i<len(points)-1 else points[-1]
        vx,vy,vz=(b[k]-a[k] for k in range(3))
        mag=math.hypot(vx,vy)
        if mag<1e-7: # choose perpendicular to local tangent with stable fallback
            off=(width*.5,0,0)
        else:off=(-vy/mag*width*.5,vx/mag*width*.5,0)
        vertices.extend([(p[0]-off[0],p[1]-off[1],p[2]),
                         (p[0]+off[0],p[1]+off[1],p[2])])
    edge_count=len(points) if closed else len(points)-1
    for i in range(edge_count):
        j=(i+1)%len(points);a=2*i;b=2*j
        faces.extend([(a,a+1,b),(a+1,b+1,b),(b,a+1,a),(b,a+1,b+1)])
    return vertices,faces

def make_halter(arm, material):
    import bpy
    paths={"noseband":(nose_loop(),True),
           "cheek_L":(cheek_path("L"),False),
           "cheek_R":(cheek_path("R"),False),
           "crownpiece":(crown_loop(),False),
           "throatlatch":(throat_loop(),False)}
    objects=[]
    for name,(points,closed) in paths.items():
        verts,faces=strap_surface(points,closed=closed)
        mesh=bpy.data.meshes.new("halter_"+name+"_mesh")
        mesh.from_pydata(verts,[],faces);mesh.update()
        obj=bpy.data.objects.new("halter_"+name,mesh)
        bpy.context.collection.objects.link(obj)
        mesh.materials.append(material)
        group=obj.vertex_groups.new(name="head")
        group.add(list(range(len(verts))),1.0,"REPLACE")
        obj.parent=arm
        modifier=obj.modifiers.new("halter_follows_head","ARMATURE")
        modifier.object=arm
        objects.append(obj)
    return objects
