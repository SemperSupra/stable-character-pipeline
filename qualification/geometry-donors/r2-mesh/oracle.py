#!/usr/bin/env python3
"""Independent, original binary-STL/CSG oracle; Python stdlib only."""
import collections
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

def main():
    out=HERE/"results"
    out.mkdir(parents=True,exist_ok=True)
    reference_volume=volume_reference()
    data={"schema":"procedural-mesh-interchange-receipt/v1","independent_reference_volume":reference_volume,"models":{}}
    for donor in MODELS:
        try:
            data["models"][donor]=inspect(out/(donor+".stl"),reference_volume)
        except Exception as ex:
            data["models"][donor]={"status":"FAIL","issues":["HARNESS_OR_FILE:"+str(ex)]}
    data["status"]="PASS" if all(x["status"]=="PASS" for x in data["models"].values()) else "FAIL"
    (out/"mesh-oracle.json").write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print(json.dumps(data,sort_keys=True))
    sys.exit(data["status"]!="PASS")

if __name__=="__main__":main()
