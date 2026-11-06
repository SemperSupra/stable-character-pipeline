"""Geometry-only independent validation of a caudal pose-bone segment witness.

The verified segment is a centerline, not an anatomical or skinned surface.
Endpoints remain native-source claims; this checks internal consistency only.
"""
import math

REQUIRED={"bone", "root_distance_to_bone_centerline_m", "bone_segment_fraction",
          "nearest_bone_centerline_point_m", "bone_head_world_m", "bone_tail_world_m"}

def xyz(v):
    if type(v) not in (tuple, list) or len(v)!=3 or any(type(x) not in (float,int) or not math.isfinite(x) for x in v):
        raise ValueError("invalid centerline coordinate")
    return tuple(float(x) for x in v)

def verify(root, witness):
    if type(witness)!=dict or set(witness)!=REQUIRED:
        raise ValueError("unknown/missing caudal centerline witness fields")
    root=xyz(root)
    a,b,q=(xyz(witness[k]) for k in ("bone_head_world_m","bone_tail_world_m","nearest_bone_centerline_point_m"))
    v=tuple(b[i]-a[i] for i in range(3))
    norm2=sum(x*x for x in v)
    if not .001**2 < norm2 < 2.**2:
        raise ValueError("unbounded caudal segment")
    t=max(0.,min(1.,sum((root[i]-a[i])*v[i] for i in range(3))/norm2))
    projected=tuple(a[i]+t*v[i] for i in range(3))
    claimed_t=witness["bone_segment_fraction"]
    claimed_d=witness["root_distance_to_bone_centerline_m"]
    if type(claimed_t) not in (float,int) or type(claimed_d) not in (float,int) or not math.isfinite(claimed_t) or not math.isfinite(claimed_d):
        raise ValueError("invalid numeric caudal projection")
    if abs(t-claimed_t)>1e-5 or math.dist(projected,q)>1e-5 or claimed_d<0 or abs(claimed_d-math.dist(root,projected))>1e-5:
        raise ValueError("caudal nearest-line projection inconsistent")
    return math.dist(root,projected)
