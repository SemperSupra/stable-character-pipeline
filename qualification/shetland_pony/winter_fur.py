"""Original double-length, skinned geometric fur on actual Blender mesh triangles.

GLB requires mesh fibers, not nonportable Blender particle/hair curves.
Synthetic geometric guard hairs and undercoat are a first native-fur stage,
not a photographic/veterinary-validated Shetland pelt.
"""
import bisect,math,random
SEED=20261106
SOURCES={"continuous_shetland_barrel_rump_shoulder":6500,
         "crest":1500,"cheek":450,"muzzle":250}

def count_for(name):
    if name in SOURCES:return SOURCES[name]
    if name.startswith(("front_","hind_")) and name.endswith(("_upper","_lower","_fetlock")):return 210
    if name.startswith("continuous_") and name.endswith("_limb"):return 680
    if name=="sculpt_sloping_neck":return 1500
    if name=="sculpt_equine_brow_bridge_muzzle":return 700
    return 0

def sample_bary(a,b,c,r,s):
    if not (0<=r<=1 and 0<=s<=1):raise ValueError("invalid barycentric sample")
    t=math.sqrt(r);w=(1-t,t*(1-s),t*s)
    return tuple(sum(w[j]*v[k] for j,v in enumerate((a,b,c))) for k in range(3)),w

def fiber(origin,normal,length,width,seed):
    if not .008<=length<=.07 or not .0002<=width<=.003:raise ValueError("bad fiber size")
    n=normal
    norm=math.sqrt(sum(q*q for q in n))
    if norm<1e-6:raise ValueError("bad normal")
    n=tuple(x/norm for x in n)
    rng=random.Random(seed)
    d=tuple(.82*n[i]+v for i,v in enumerate((-.34,rng.uniform(-.22,.22),.07)))
    mag=math.sqrt(sum(x*x for x in d));d=tuple(x/mag for x in d)
    cross=(n[1]*d[2]-n[2]*d[1], n[2]*d[0]-n[0]*d[2], n[0]*d[1]-n[1]*d[0])
    cm=math.sqrt(sum(x*x for x in cross))
    if cm<1e-6:cross=(0,1,0);cm=1.
    cross=tuple(x/cm for x in cross)
    vertices=[]
    for fraction,scale in ((0,.95),(.55,.55),(1,.025)):
        center=tuple(origin[k]+.001*n[k]+d[k]*length*fraction for k in range(3))
        for sign in (-1,1):
            vertices.append(tuple(center[k]+sign*width*scale*cross[k] for k in range(3)))
    return vertices,((0,1,2),(1,3,2),(2,3,4),(3,5,4))

def create_fur_surface(source,arm,base,white,count,seed):
    import bpy
    from mathutils import Vector
    mesh=source.data
    mesh.calc_loop_triangles()
    M=arm.matrix_world.inverted()@source.matrix_world
    points=[tuple(M@v.co) for v in mesh.vertices]
    tri=[];cdf=[];area=0.
    for t in mesh.loop_triangles:
        ids=tuple(t.vertices)
        v=[Vector(points[k]) for k in ids]
        normal=(v[1]-v[0]).cross(v[2]-v[0])
        a=normal.length*.5
        if a<1e-10:continue
        area+=a;cdf.append(area)
        tri.append((ids,tuple(normal.normalized()),mesh.polygons[t.polygon_index].material_index))
    if not tri:raise ValueError("no source mesh faces")
    names={x.index:x.name for x in source.vertex_groups}
    rng=random.Random(seed)
    vertices=[];faces=[];colors=[];bone_groups={}
    for i in range(count):
        index=min(bisect.bisect_left(cdf,rng.random()*area),len(tri)-1)
        ids,n,paint=tri[index]
        pos,bary=sample_bary(*(points[k] for k in ids),rng.random(),rng.random())
        long_guard=(i%4==0)
        length=rng.uniform(.027,.051) if long_guard else rng.uniform(.013,.025)
        width=rng.uniform(.00050,.00098) if long_guard else rng.uniform(.00031,.00061)
        strand,polys=fiber(pos,n,length,width,seed+i*197)
        start=len(vertices)
        vertices.extend(strand)
        faces.extend(tuple(start+k for k in p) for p in polys)
        colors.extend([(1 if paint and white else 0)]*len(polys))
        skin={}
        for vid,w in zip(ids,bary):
            for g in mesh.vertices[vid].groups:
                k=names.get(g.group)
                if k:skin[k]=skin.get(k,0.)+w*g.weight
        total=sum(skin.values())
        if total<.9:raise ValueError("source mesh missing valid skin")
        for k,weight in skin.items():
            if weight>1e-5:
                bone_groups.setdefault(k,[]).append((start,weight/total))
    data=bpy.data.meshes.new("fur_geometry_"+source.name)
    data.from_pydata(vertices,[],faces);data.update()
    obj=bpy.data.objects.new("FUR_skinned_"+source.name,data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(base)
    if white:data.materials.append(white)
    for poly,color in zip(data.polygons,colors):
        poly.material_index=color;poly.use_smooth=True
    for name,items in bone_groups.items():
        group=obj.vertex_groups.new(name=name)
        for start,weight in items:
            group.add(list(range(start,start+6)),weight,"REPLACE")
    obj.parent=arm
    mod=obj.modifiers.new("fur_deforms_with_source_skin","ARMATURE")
    mod.object=arm
    return {"source":source.name,"strands":count,"vertices":len(vertices),"triangles":len(faces)}

def create_coat(arm,base,white=None):
    import bpy
    originals=[o for o in list(bpy.context.scene.objects) if o.type=="MESH" and count_for(o.name)>0]
    total=sum(count_for(o.name) for o in originals)
    if not 2500<=total<=20000:raise ValueError("no candidate or oversized groom")
    receipt=[]
    for i,source in enumerate(originals):
        receipt.append(create_fur_surface(source,arm,base,white,count_for(source.name),SEED+i*521))
    return {"schema":"equine.fur.skinned.v1","total_strands":total,
            "source":"deterministic_two_length_geometry","glb_export":"skinned_triangles",
            "visual_quality":"UNACCEPTED","sources":receipt}
