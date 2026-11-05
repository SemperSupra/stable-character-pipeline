"""Procedural continuous original Shetland torso with conformal pinto surface mask.

CPU deterministic, Blender import only in create_body_surface(). Source-original
mesh replaces three disconnected UV-ellipsoids; does NOT fix limb joint anatomy.
"""
import math

STATIONS=[
    (-.78,.80,.060,.100),
    (-.70,.81,.205,.255),
    (-.54,.815,.294,.325),
    (-.35,.805,.315,.343),
    (-.14,.795,.324,.330),
    ( .10,.810,.315,.332),
    ( .28,.833,.302,.330),
    ( .43,.860,.245,.295),
    ( .59,.885,.080,.135),
]
RINGS=61
SIDES=32

def station_at(x):
    if x<=STATIONS[0][0]:return STATIONS[0][1:]
    if x>=STATIONS[-1][0]:return STATIONS[-1][1:]
    for index in range(len(STATIONS)-1):
        a,b=STATIONS[index],STATIONS[index+1]
        if a[0]<=x<=b[0]:
            t=(x-a[0])/(b[0]-a[0])
            # Cubic Hermite uses neighbor station derivatives, smoothing barrel
            # without kinks or unsupported overhung control profiles.
            result=[]
            for field in (1,2,3):
                left=STATIONS[max(0,index-1)]
                right=STATIONS[min(len(STATIONS)-1,index+2)]
                m0=(b[field]-left[field])/(b[0]-left[0])
                m1=(right[field]-a[field])/(right[0]-a[0])
                dx=b[0]-a[0]
                value=(2*t**3-3*t*t+1)*a[field]+(t**3-2*t*t+t)*dx*m0+(-2*t**3+3*t*t)*b[field]+(t**3-t*t)*dx*m1
                result.append(value)
            return tuple(result)
    raise ValueError("no x station")

def pinto_patch(x,y,z):
    """White pinto coat drawn *within the same mesh*, not raised skin blobs."""
    if abs(y)<.04:
        # back/underside can be white; not a hard dorsal stripe for all x
        pass
    edge=.028*math.sin(12.0*x+4.5*y)+.019*math.sin(31*x-6*y)
    shoulder=(.13+edge<x<.38+edge and z>.69+edge)
    belly=(-.30+edge<x<.28-edge and z<.69-edge)
    neck_base=(.42+edge<x<.53 and z>.92)
    rump_mark=(-.60<x<-.43+edge and z>1.035+edge)
    return shoulder or belly or neck_base or rump_mark

def geometry(rings=RINGS,sides=SIDES,pinto=False):
    if rings<8 or sides<8 or rings>256 or sides>128:
        raise ValueError("unbounded topology resolution")
    points=[];faces=[];masks=[]
    for i in range(rings):
        x=STATIONS[0][0]+(STATIONS[-1][0]-STATIONS[0][0])*i/(rings-1)
        center_z,wide,high=station_at(x)
        for j in range(sides):
            theta=2*math.pi*j/sides
            points.append((x,wide*math.cos(theta),center_z+high*math.sin(theta)))
    for i in range(rings-1):
        for j in range(sides):
            a=i*sides+j
            b=i*sides+(j+1)%sides
            c=(i+1)*sides+j
            d=(i+1)*sides+(j+1)%sides
            faces.extend([(a,b,c),(b,d,c)])
    first=len(points)
    points.append((STATIONS[0][0],0.0,STATIONS[0][1]))
    last=len(points)
    points.append((STATIONS[-1][0],0.0,STATIONS[-1][1]))
    for j in range(sides):
        j2=(j+1)%sides
        faces.append((first,j2,j)) # left cap outward -X
        faces.append((last,(rings-1)*sides+j,(rings-1)*sides+j2))
    for f in faces:
        if pinto:
            x=sum(points[k][0] for k in f)/3
            y=sum(points[k][1] for k in f)/3
            z=sum(points[k][2] for k in f)/3
            masks.append(int(pinto_patch(x,y,z)))
        else:masks.append(0)
    return points,faces,masks

def create_body_surface(arm,coat_material,white_material=None):
    import bpy
    points,faces,masks=geometry(pinto=white_material is not None)
    mesh=bpy.data.meshes.new("original_continuous_torso_topology")
    mesh.from_pydata(points,[],faces)
    mesh.update()
    obj=bpy.data.objects.new("continuous_shetland_barrel_rump_shoulder",mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(coat_material)
    if white_material:mesh.materials.append(white_material)
    for face,mask in zip(mesh.polygons,masks):
        face.use_smooth=True
        face.material_index=mask
    body=obj.vertex_groups.new(name="body")
    neck=obj.vertex_groups.new(name="neck")
    for i,p in enumerate(points):
        x=p[0]
        n=0.0 if x<=.28 else .23*min(1.,(x-.28)/(.59-.28))
        body.add([i],1.0-n,"REPLACE")
        if n>0:neck.add([i],n,"REPLACE")
    obj.parent=arm
    mod=obj.modifiers.new("continuous_armature_skin","ARMATURE")
    mod.object=arm
    return obj
