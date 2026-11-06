"""Deterministic original Shetland hair-card curvature and source-skin preservation.

Four interpolated segments per long hair card, source root unchanged, tapered
width preserved, hanging z profile added. Blender only used for mesh adapter.
"""
import math

ROWS=5
VERTS_PER_CARD=10

def curve_card(points, index, bone):
    if len(points)!=4 or not isinstance(index,int) or index<0:
        raise ValueError("invalid hair card")
    if bone not in ("neck","head","tail_1","tail_2","tail_3"):
        raise ValueError("unknown source skin")
    pts=[tuple(float(x) for x in p) for p in points]
    if any(len(p)!=3 or any(not math.isfinite(x) for x in p) for p in pts):
        raise ValueError("nonfinite hair geometry")
    sag={"neck":.075,"head":.040,"tail_1":.027,"tail_2":.027,"tail_3":.027}[bone]
    vertices=[]
    for r in range(ROWS):
        t=r/(ROWS-1)
        arc=math.sin(math.pi*t)
        # No random per-frame movement; strand-specific deterministic bias.
        curve_x=.008*arc*math.sin(index*1.317)
        curve_y=.011*arc*math.cos(index*.887)
        curve_z=-sag*(t*t+.45*arc)
        if r==0:
            # The follicle roots are immutable source anchors, bit-exact.
            vertices.extend((pts[0],pts[1]))
            continue
        left=tuple(pts[0][k]*(1-t)+pts[2][k]*t for k in range(3))
        right=tuple(pts[1][k]*(1-t)+pts[3][k]*t for k in range(3))
        center=tuple((left[k]+right[k])*.5 for k in range(3))
        half=tuple((right[k]-left[k])*.5 for k in range(3))
        # Progressive needle-tip taper suppresses the previous broad,
        # brush-like card ends. Never collapse to exact zero-area triangles.
        tip_width=.09 if bone.startswith("tail_") else .12
        width_scale=tip_width+(1-tip_width)*(1-t)**1.3
        for side_sign in (-1,1):
            vertices.append((center[0]+side_sign*half[0]*width_scale+curve_x,
                             center[1]+side_sign*half[1]*width_scale+curve_y,
                             center[2]+side_sign*half[2]*width_scale+curve_z))
    faces=[]
    for r in range(ROWS-1):
        a=2*r;b=2*(r+1)
        faces.extend(((a,a+1,b),(a+1,b+1,b)))
    if vertices[0]!=pts[0] or vertices[1]!=pts[1]:
        # sin(pi*0)=0, so the fixed root must never move.
        raise ValueError("lost exact follicle root")
    return vertices,faces

def make_curved_groom(groom):
    """Replace four-vertex originals with UV-backed 10-vertex curved cards.

    Source object, material, armature modifier and skin group names survive.
    Returns exact per-card source bone owners for world-space motion solving.
    """
    import bpy
    mesh=groom.data
    if len(mesh.vertices)!=1050*4:
        raise ValueError("unexpected original card count")
    old_groups=groom.vertex_groups
    bones=[];vertices=[];faces=[]
    for i in range(1050):
        ids=range(i*4,i*4+4)
        owners=[mesh.vertices[k].groups for k in ids]
        if any(len(w)!=1 or abs(w[0].weight-1.)>1e-6 for w in owners):
            raise ValueError("expected one source bone per card")
        owner=old_groups[owners[0][0].group].name
        if any(old_groups[w[0].group].name!=owner for w in owners):
            raise ValueError("mixed source card bone")
        bones.append(owner)
        points=[tuple(mesh.vertices[k].co) for k in ids]
        vv,ff=curve_card(points,i,owner)
        offset=len(vertices)
        vertices.extend(vv)
        faces.extend(tuple(offset+j for j in f) for f in ff)
    new=bpy.data.meshes.new("original_longhair_curved_5rows")
    new.from_pydata(vertices,[],faces)
    new.update()
    for material in mesh.materials:
        new.materials.append(material)
    uv=new.uv_layers.new(name="LongHairUV")
    for poly in new.polygons:
        poly.use_smooth=True
        for li in poly.loop_indices:
            index=new.loops[li].vertex_index%VERTS_PER_CARD
            uv.data[li].uv=(float(index%2),float(index//2)/(ROWS-1))
    original=mesh
    groom.data=new
    # Blender may clear Object vertex-group slots when replacing mesh data.
    # Recreate exactly the captured source labels, then rebind each follicle
    # to its prior owner. Never silently remap names to index positions.
    for label in sorted(set(bones)):
        if groom.vertex_groups.get(label) is None:
            groom.vertex_groups.new(name=label)
    for i,bone in enumerate(bones):
        group=groom.vertex_groups.get(bone)
        if group is None:raise ValueError("unable to recreate original skin group")
        group.add(list(range(i*VERTS_PER_CARD,(i+1)*VERTS_PER_CARD)),1.,"REPLACE")
    if original.users==0:bpy.data.meshes.remove(original)
    if len(groom.data.vertices)!=1050*VERTS_PER_CARD:
        raise ValueError("curved guide topology inconsistent")
    return bones
