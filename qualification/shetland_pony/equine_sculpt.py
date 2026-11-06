"""Original equine head/neck and continuous limbs; independent Blender-free topology."""
import math

# x,z,width,depth: forehead -> long tapering nasal bridge -> distinct soft muzzle
# Shorter convex equine nasal bridge, broad forehead and discrete full muzzle.
# The preceding long, descending oval stack produced an aardvark-like profile.
HEAD=((.615,1.18,.113,.146),(.678,1.174,.148,.176),
      (.750,1.146,.155,.170),(.822,1.082,.138,.151),
      (.895,1.005,.118,.127),(.964,.934,.106,.104),
      (1.032,.891,.108,.090),(1.104,.876,.114,.083),
      (1.135,.867,.119,.073))
NECK=((.310,.86,.215,.235),(.383,.927,.206,.223),(.46,1.005,.181,.207),(.54,1.08,.153,.183),(.615,1.148,.131,.157),(.682,1.173,.118,.14))

# x offset, z, sagittal/lateral radii, upper/lower/fetlock blending
FRONT=((-.01,.815,.107,.103,(1,0,0)),(.01,.65,.099,.085,(1,0,0)),(0,.48,.082,.074,(.63,.37,0)),(.003,.37,.067,.065,(.1,.9,0)),(.015,.265,.062,.06,(0,.8,.2)),(.026,.12,.072,.067,(0,.1,.9)))
HIND=((-.02,.80,.136,.115,(1,0,0)),(-.065,.65,.122,.101,(1,0,0)),(.008,.48,.084,.081,(.6,.4,0)),(-.021,.35,.068,.067,(.1,.9,0)),(.01,.26,.061,.060,(0,.8,.2)),(.028,.12,.073,.068,(0,.1,.9)))

def sweep(profile,sides=24,steps=4):
    if len(profile)<3 or sides<8 or sides>64 or steps<2 or steps>12:raise ValueError("bounds")
    count=(len(profile)-1)*steps+1
    centers=[]
    for i in range(count):
        q=i/steps;j=min(int(q),len(profile)-2);u=q-j;u=u*u*(3-2*u)
        centers.append(tuple(float(profile[j][k]*(1-u)+profile[j+1][k]*u) for k in range(4)))
    vertices=[]
    for i,(x,z,wide,depth) in enumerate(centers):
        left=centers[max(0,i-1)];right=centers[min(count-1,i+1)]
        dx=right[0]-left[0];dz=right[1]-left[1]
        norm=math.hypot(dx,dz)
        if norm<1e-5:raise ValueError("collapsed centerline")
        for j in range(sides):
            angle=2*math.pi*j/sides
            vertices.append((x-depth*math.sin(angle)*dz/norm,
                wide*math.cos(angle),z+depth*math.sin(angle)*dx/norm))
    faces=[]
    for i in range(count-1):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides;c=(i+1)*sides+j;d=(i+1)*sides+(j+1)%sides
            faces.extend(((a,b,c),(b,d,c)))
    start=len(vertices);vertices.append((centers[0][0],0,centers[0][1]))
    stop=len(vertices);vertices.append((centers[-1][0],0,centers[-1][1]))
    for j in range(sides):
        k=(j+1)%sides
        faces.extend(((start,k,j),(stop,(count-1)*sides+j,(count-1)*sides+k)))
    return vertices,faces

def leg(prefix,side,sides=20,steps=3):
    if prefix not in ("front","hind") or side not in ("L","R"):raise ValueError("invalid named limb")
    profile=FRONT if prefix=="front" else HIND
    x0=.40 if prefix=="front" else -.48
    y0=-.205 if side=="L" else .205
    rings=(len(profile)-1)*steps+1
    vertices=[];weights=[]
    for i in range(rings):
        q=i/steps;j=min(int(q),len(profile)-2);u=q-j;u=u*u*(3-2*u)
        def lerp(k):return profile[j][k]*(1-u)+profile[j+1][k]*u
        x,z,rx,ry=x0+lerp(0),lerp(1),lerp(2),lerp(3)
        wt=tuple(profile[j][4][k]*(1-u)+profile[j+1][4][k]*u for k in range(3))
        for t in range(sides):
            a=2*math.pi*t/sides
            vertices.append((x+rx*math.cos(a),y0+ry*math.sin(a),z));weights.append(wt)
    faces=[]
    for i in range(rings-1):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides;c=(i+1)*sides+j;d=(i+1)*sides+(j+1)%sides
            faces.extend(((a,c,b),(b,c,d)))
    n=len(vertices);vertices.append((x0+profile[0][0],y0,profile[0][1]));weights.append((1,0,0))
    m=len(vertices);vertices.append((x0+profile[-1][0],y0,profile[-1][1]));weights.append((0,0,1))
    for j in range(sides):
        k=(j+1)%sides
        faces.extend(((n,j,k),(m,(rings-1)*sides+k,(rings-1)*sides+j)))
    return vertices,faces,weights

def build_mesh(name,vertices,faces,weights,arm,material):
    import bpy
    mesh=bpy.data.meshes.new(name+"_mesh")
    mesh.from_pydata(vertices,[],faces);mesh.update()
    from wool_texture import assign_uv
    if name.startswith("continuous_") and name.endswith("_limb"):
        assign_uv(mesh,20)
    else:
        assign_uv(mesh,24)
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    mesh.materials.append(material)
    for poly in mesh.polygons:poly.use_smooth=True
    for idx,weights_at_vertex in enumerate(weights):
        for bone,amount in weights_at_vertex.items():
            if amount>1e-6:
                group=obj.vertex_groups.get(bone) or obj.vertex_groups.new(name=bone)
                group.add([idx],amount,"REPLACE")
    obj.parent=arm;mod=obj.modifiers.new("equine_continuous_skin","ARMATURE");mod.object=arm
    return obj

def four_joint_skin_weights(point,prior,prefix,side):
    if prefix not in ("front","hind") or side not in ("L","R"):
        raise ValueError("invalid limb")
    if abs(sum(prior)-1)>1e-8:
        raise ValueError("un-normalized original bone weights")
    # Intermediate elbow→carpus forearm / stifle→hock gaskin now carries
    # geometric deformation rather than existing merely as an unweighted bone.
    transition=max(0.,min(1.,(.77-point[2])/.26))
    middle="forearm" if prefix=="front" else "stifle"
    bones=(f"{prefix}_{side}_upper",f"{prefix}_{side}_{middle}",
           f"{prefix}_{side}_lower",f"{prefix}_{side}_fetlock")
    weights=(prior[0]*(1-transition),prior[0]*transition,prior[1],prior[2])
    return {b:v for b,v in zip(bones,weights) if v>1e-6}

def create_equine_sculpt(arm,coat,face_material):
    v,f=sweep(NECK)
    count=(len(NECK)-1)*4+1
    w=[]
    for i in range(count):
        neck=.20+.80*i/(count-1)
        w.extend([{"neck":neck,"body":1-neck} for _ in range(24)])
    w.extend([{"body":.8,"neck":.2},{"neck":1.}])
    build_mesh("sculpt_sloping_neck",v,f,w,arm,coat)
    v,f=sweep(HEAD)
    build_mesh("sculpt_equine_brow_bridge_muzzle",v,f,[{"head":1.} for _ in v],arm,face_material)
    for prefix in ("front","hind"):
        for side in ("L","R"):
            v,f,w=leg(prefix,side)
            assignments=[four_joint_skin_weights(point,ws,prefix,side)
                         for point,ws in zip(v,w)]
            build_mesh(f"continuous_{prefix}_{side}_limb",v,f,assignments,arm,coat)
