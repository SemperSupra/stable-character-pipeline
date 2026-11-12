#!/usr/bin/env python3
"""Independent, original binary-STL/CSG oracle; Python stdlib only."""
import collections
import itertools
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys

HERE=Path(__file__).resolve().parent
MODELS=("sdfx-uniform","sdfx-octree","gsdf-flat")

def reference(p):
    x,y,z=p
    sphere=math.sqrt(x*x+y*y+z*z)-1
    q=[abs(x)-1.4,abs(y)-0.25,abs(z)-0.25]
    box=math.sqrt(sum(max(v,0)**2 for v in q))+min(max(q),0)
    return min(sphere,box)

def volume_reference():
    # Fixed independent midpoint rule at 0.0625 units, 48^3 samples.
    n=48
    cell=3.0/n
    count=0
    for i in range(n):
        x=-1.5+(i+0.5)*cell
        for j in range(n):
            y=-1.5+(j+0.5)*cell
            for k in range(n):
                z=-1.5+(k+0.5)*cell
                count+=reference((x,y,z))<0
    return count*cell**3

def inspect(path,reference_volume):
    blob=path.read_bytes()
    if len(blob)<84:raise ValueError("truncated_stl")
    count=struct.unpack_from("<I",blob,80)[0]
    if not count or len(blob)!=84+count*50:raise ValueError("binary_stl_size_mismatch")
    degree=collections.Counter()
    degree_direction=collections.Counter()
    vertex_bounds=[[float("inf")]*3,[-float("inf")]*3]
    max_surface_error=0.0
    degenerate=0
    volume=0.0
    # Sample every triangle vertex; use exact float32 coordinates as topology keys.
    for i in range(count):
        f=struct.unpack_from("<12fH",blob,84+50*i)
        v=(f[3:6],f[6:9],f[9:12])
        for p in v:
            if not all(math.isfinite(t) for t in p):raise ValueError("nonfinite_vertex")
            max_surface_error=max(max_surface_error,abs(reference(p)))
            for d in range(3):
                vertex_bounds[0][d]=min(vertex_bounds[0][d],p[d])
                vertex_bounds[1][d]=max(vertex_bounds[1][d],p[d])
        ab=[v[1][d]-v[0][d] for d in range(3)]
        ac=[v[2][d]-v[0][d] for d in range(3)]
        cross=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
        if sum(t*t for t in cross)<1e-16:degenerate+=1
        volume+=sum(v[0][d]*cross[d] for d in range(3))/6.0
        for a,b in ((0,1),(1,2),(2,0)):
            edge=tuple(sorted((v[a],v[b])))
            degree[edge]+=1
            degree_direction[(v[a],v[b])]+=1
    nonmanifold=sum(inc!=2 for inc in degree.values())
    reversed_edges=sum(inc==2 and degree_direction.get((e[0],e[1]),0)!=1 for e,inc in degree.items())
    rel_volume_error=abs(abs(volume)-reference_volume)/reference_volume
    issues=[]
    if degenerate:issues.append("DEGENERATE_TRIANGLES")
    if nonmanifold:issues.append("NON_MANIFOLD_EDGES")
    if reversed_edges:issues.append("INCONSISTENT_EDGE_WINDING")
    if max_surface_error>0.12:issues.append("SURFACE_RESIDUAL_EXCEEDS_TOLERANCE")
    if rel_volume_error>0.15:issues.append("VOLUME_RELATIVE_ERROR_EXCEEDS_TOLERANCE")
    if any(abs(v)>1.52 for p in vertex_bounds for v in p):issues.append("BOUNDS_ESCAPED")
    if vertex_bounds[1][0]<1.30 or vertex_bounds[0][0]>-1.30:issues.append("MISSING_BOX_EXTENT")
    return {
        "status":"PASS" if not issues else "FAIL",
        "sha256":hashlib.sha256(blob).hexdigest(),
        "triangle_count":count,"unique_edges":len(degree),
        "nonmanifold_edges":nonmanifold,"inconsistent_winding_edges":reversed_edges,
        "degenerate_triangles":degenerate,
        "signed_volume":volume,"independent_reference_volume":reference_volume,
        "relative_volume_error":rel_volume_error,
        "max_abs_csg_surface_residual":max_surface_error,
        "bounds_min":vertex_bounds[0],"bounds_max":vertex_bounds[1],
        "issues":issues,
    }

def conservative_vertex_weld(raw_path, output_path, tolerance):
    """Loss-bounded G4 adapter; original STL is unchanged and retained."""
    blob=raw_path.read_bytes()
    count=struct.unpack_from("<I",blob,80)[0]
    points=[]
    point_ids={}
    triangles=[]
    for i in range(count):
        values=struct.unpack_from("<12fH",blob,84+50*i)
        face=[]
        for vertex in (values[3:6],values[6:9],values[9:12]):
            if vertex not in point_ids:
                point_ids[vertex]=len(points)
                points.append(vertex)
            face.append(point_ids[vertex])
        triangles.append(face)
    parents=list(range(len(points)))
    buckets=collections.defaultdict(list)
    def find(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]]
            i=parents[i]
        return i
    for i,p in enumerate(points):
        cell=tuple(math.floor(v/tolerance) for v in p)
        for step in itertools.product((-1,0,1),repeat=3):
            neighbor=tuple(cell[j]+step[j] for j in range(3))
            for other in buckets.get(neighbor,()):
                if math.dist(p,points[other])<=tolerance:
                    a,b=find(i),find(other)
                    parents[max(a,b)]=min(a,b)
        buckets[cell].append(i)
    parents=[find(i) for i in range(len(points))]
    max_displacement=max(math.dist(p,points[parents[i]]) for i,p in enumerate(points))
    if max_displacement>tolerance:
        raise ValueError("weld_displacement_exceeds_limit")
    out=bytearray(b"Original synthetic gsdf STL; conservative G4 weld".ljust(80,b"\\0"))
    out.extend(struct.pack("<I",count))
    for face in triangles:
        v=[points[parents[i]] for i in face]
        a=[v[1][j]-v[0][j] for j in range(3)]
        b=[v[2][j]-v[0][j] for j in range(3)]
        cross=(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
        norm=math.sqrt(sum(t*t for t in cross))
        if norm<=1e-12:raise ValueError("weld_created_degenerate_triangle")
        normal=[t/norm for t in cross]
        out.extend(struct.pack("<12fH",*normal,*v[0],*v[1],*v[2],0))
    output_path.write_bytes(out)
    return {"strategy":"G4 conservative vertex welding; unchanged donor source",
            "tolerance":tolerance,"max_displacement":max_displacement,
            "source_sha256":hashlib.sha256(blob).hexdigest(),
            "repaired_sha256":hashlib.sha256(out).hexdigest(),
            "original_unique_vertices":len(points),
            "canonical_unique_vertices":len(set(parents)),
            "original_triangles":count,"repaired_triangles":count}

def main():
    out=HERE/"results"
    out.mkdir(parents=True,exist_ok=True)
    reference_volume=volume_reference()
    data={"schema":"procedural-mesh-interchange-receipt/v1","independent_reference_volume":reference_volume,"models":{}}
    for donor in MODELS:
        try:
            raw_path=out/(donor+".stl")
            raw=inspect(raw_path,reference_volume)
            if donor=="gsdf-flat" and raw["issues"]==["NON_MANIFOLD_EDGES"]:
                destination=out/"gsdf-welded.stl"
                adapter=conservative_vertex_weld(raw_path,destination,3e-7)
                corrected=inspect(destination,reference_volume)
                data["models"][donor]={
                    "status":"PASS_WITH_ADAPTER" if corrected["status"]=="PASS" else "FAIL",
                    "raw":raw,"adapter":adapter,"corrected":corrected,
                }
            else:
                data["models"][donor]=raw
        except Exception as ex:
            data["models"][donor]={"status":"FAIL","issues":["HARNESS_OR_FILE:"+str(ex)]}
    observed=[item["status"] for item in data["models"].values()]
    data["status"]=(
        "PASS" if all(v=="PASS" for v in observed)
        else "PASS_WITH_ADAPTER" if all(v in ("PASS","PASS_WITH_ADAPTER") for v in observed)
        else "FAIL"
    )
    (out/"mesh-oracle.json").write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print(json.dumps(data,sort_keys=True))
    sys.exit(data["status"]=="FAIL")

if __name__=="__main__":main()
