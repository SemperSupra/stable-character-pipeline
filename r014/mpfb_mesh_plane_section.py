"""Triangle-plane surface intersections with explicit closed-loop qualification.

R014 native Blender geometry: this module is independent of MPFB/Blender and
can be tested against known synthetic closed meshes on any disposable CPU.
Not an anatomical landmark classifier and never silently converts units.
"""
from collections import defaultdict
import math
import numpy as np

def plane_section(vertices,faces,z,quant=1e-6):
    verts=np.asarray(vertices,dtype=np.float64)
    triangles=np.asarray(faces,dtype=np.int64)
    assert verts.ndim==2 and verts.shape[1]==3 and np.isfinite(verts).all()
    assert triangles.ndim==2 and triangles.shape[1]==3
    assert len(triangles)>0 and triangles.min()>=0 and triangles.max()<len(verts)
    assert math.isfinite(z) and quant>0
    v=verts[triangles]
    # Never assume every triangle crosses; no extrapolation across holes.
    signed=v[:,:,2]-z
    near=(np.abs(signed)<1e-10).any(axis=1)
    cross=[]
    for a,b in ((0,1),(1,2),(2,0)):
        za,zb=signed[:,a],signed[:,b]
        mask=((za<0)&(zb>0))|((za>0)&(zb<0))
        fraction=np.zeros(len(triangles),dtype=np.float64)
        fraction[mask]=-za[mask]/(zb[mask]-za[mask])
        points=v[:,a,:2]+fraction[:,None]*(v[:,b,:2]-v[:,a,:2])
        cross.append((mask,points))
    hits=np.stack([p[0] for p in cross],axis=1)
    count=hits.sum(axis=1)
    valid=(count==2)&(~near)
    endpoints=np.stack([p[1] for p in cross],axis=1)[valid]
    selected=hits[valid]
    pairs=endpoints[selected].reshape(-1,2,2)
    # A true mesh-plane intersection is a graph of segments; reconstruct
    # connected cycles instead of incorrectly treating bounding boxes as girths.
    adj=defaultdict(list)
    edges=[]
    degenerate=0
    for segment in pairs:
        a=tuple(int(x) for x in np.rint(segment[0]/quant))
        b=tuple(int(x) for x in np.rint(segment[1]/quant))
        if a==b:
            degenerate+=1
            continue
        length=float(np.linalg.norm(segment[0]-segment[1]))
        idx=len(edges)
        edges.append((a,b,length))
        adj[a].append((b,idx))
        adj[b].append((a,idx))
    visited=set()
    cycles=[]
    open_components=0
    ambiguous_components=0
    for first in sorted(adj):
        if first in visited:continue
        q=[first]
        nodes=set()
        edgeids=set()
        while q:
            node=q.pop()
            if node in nodes:continue
            nodes.add(node);visited.add(node)
            for other,ei in adj[node]:
                edgeids.add(ei)
                if other not in nodes:q.append(other)
        degree=[len(adj[u]) for u in nodes]
        if not all(v==2 for v in degree):
            open_components+=1
            if any(v>2 for v in degree):ambiguous_components+=1
        elif len(edgeids)==len(nodes) and len(nodes)>=3:
            perimeter=sum(edges[i][2] for i in edgeids)
            cycles.append((perimeter,len(edgeids)))
        else:open_components+=1
    cycles.sort(reverse=True)
    return {
        "plane_z_native_units":round(float(z),9),
        "crossing_triangles":int(valid.sum()),
        "coplanar_or_vertex_touching_triangles":int(near.sum()),
        "non_two_crossing_triangles":int(((count!=0)&(count!=2)).sum()),
        "degenerate_segments":degenerate,
        "graph_nodes":len(adj),
        "closed_loops":len(cycles),
        "open_components":open_components,
        "non_manifold_or_quantization_ambiguous_components":ambiguous_components,
        "largest_closed_perimeter_native_units":round(float(cycles[0][0]),9) if cycles else None,
        "total_closed_perimeter_native_units":round(float(sum(v[0] for v in cycles)),9),
        "largest_closed_loop_segments":cycles[0][1] if cycles else 0,
        "loop_perimeters_native_units":[round(float(v[0]),9) for v in cycles[:12]],
        "scope":"mesh-triangle plane-section closed polygon loop in uncalibrated native units; NOT anatomical waist/chest/hip claim"
    }

def test_synthetic():
    # Closed triangulated unit cube: each horizontal section must be a
    # single 4-unit planar loop, not a width-depth estimate.
    v=np.asarray([(x,y,z) for z in (0.,1.) for y in (0.,1.) for x in (0.,1.)],dtype=float)
    quads=((0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3))
    f=np.asarray([tri for face in quads for tri in ((face[0],face[1],face[2]),(face[0],face[2],face[3]))],dtype=int)
    single=plane_section(v,f,.317)
    assert single["closed_loops"]==1 and single["open_components"]==0,single
    assert abs(single["largest_closed_perimeter_native_units"]-4.)<1e-9,single
    double=plane_section(np.concatenate([v,v+[3.,0.,0.]]),
                         np.concatenate([f,f+len(v)]),.317)
    assert double["closed_loops"]==2 and double["open_components"]==0,double
    assert abs(double["total_closed_perimeter_native_units"]-8.)<1e-8,double
    # A missing wall triangle must fail to form a closed girth.
    missing=plane_section(v,np.delete(f,4,axis=0),.317)
    assert missing["open_components"]>=1 and missing["closed_loops"]==0,missing
    return {"status":"PASS_EXACT_CUBE_TWO_DISJOINT_CUBES_OPEN_NEGATIVE",
            "unit_cube_perimeter":single["largest_closed_perimeter_native_units"],
            "disjoint_total_perimeter":double["total_closed_perimeter_native_units"],
            "open_negative_components":missing["open_components"]}
