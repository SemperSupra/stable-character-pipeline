#!/usr/bin/env python3
"""Original two-link rig and Gaussian-sample mathematical ground truth.

No external character assets, weights, human media, copyrighted data or
third-party source. Source geometry in meters; positive Y rotation bends
the child link toward negative world Z.
"""
from __future__ import annotations
import hashlib
import itertools
import json
import math
import struct
from pathlib import Path

LENGTH, WIDTH, HEIGHT = 0.56, 0.15, 0.18
POSES = (0, 45, 90)
PAINTS = ("base", "repaint")
FACE_GRID = (7, 3, 3)
C0 = 0.28209479177387814
PALETTE = {
    "upper": (0.84, 0.17, 0.16),
    "lower_base": (0.12, 0.25, 0.86),
    "lower_repaint": (0.14, 0.77, 0.27),
}
FIELDS = ("x", "y", "z", "nx", "ny", "nz",
          "f_dc_0", "f_dc_1", "f_dc_2", "opacity",
          "scale_0", "scale_1", "scale_2",
          "rot_0", "rot_1", "rot_2", "rot_3")

def require(pose: int, paint: str):
    if pose not in POSES or paint not in PAINTS:
        raise ValueError(f"unsupported pose/paint: {pose}/{paint}")

def rotate_y(point, theta):
    x, y, z = point
    co, si = math.cos(theta), math.sin(theta)
    return (co*x + si*z, y, -si*x + co*z)

def transform(segment, pose, point):
    if segment == "upper":
        return (point[0] - LENGTH/2, point[1], point[2])
    if segment == "lower":
        center = rotate_y((LENGTH/2, 0, 0), math.radians(pose))
        rotated = rotate_y(point, math.radians(pose))
        return tuple(center[i]+rotated[i] for i in range(3))
    raise ValueError(segment)

def surface_samples(segment, pose):
    sizes = (LENGTH, WIDTH, HEIGHT)
    dims = FACE_GRID
    result = []
    for axis in range(3):
        tangents = [d for d in range(3) if d != axis]
        for sign in (-1, 1):
            for a in range(dims[tangents[0]]):
                for b in range(dims[tangents[1]]):
                    loc = [0., 0., 0.]
                    loc[axis] = sign*sizes[axis]/2
                    for d,k in zip(tangents, (a,b)):
                        loc[d] = ((k+.5)/dims[d]-.5)*sizes[d]
                    norm=[0.,0.,0.]
                    norm[axis]=float(sign)
                    if segment=="lower":
                        norm = rotate_y(norm, math.radians(pose))
                    result.append((transform(segment,pose,tuple(loc)),tuple(norm)))
    return result

def vertices(segment,pose):
    out=[]
    for signs in itertools.product((-1,1),repeat=3):
        local=tuple(signs[i]*size/2 for i,size in enumerate((LENGTH,WIDTH,HEIGHT)))
        out.append(transform(segment,pose,local))
    return out

def center(segment,pose):
    return transform(segment,pose,(0.,0.,0.))

def tip(pose):
    return rotate_y((LENGTH,0.,0.),math.radians(pose))

def colors(paint):
    return {"upper":PALETTE["upper"],
            "lower":PALETTE["lower_base"] if paint=="base" else PALETTE["lower_repaint"]}

def gaussian_rows(pose,paint):
    require(pose,paint)
    result=[]
    for seg in ("upper","lower"):
        rgb = colors(paint)[seg]
        sh=tuple((x-.5)/C0 for x in rgb)
        a=0 if seg=="upper" else math.radians(pose)
        q=(math.cos(a/2),0.,math.sin(a/2),0.)
        for pos,norm in surface_samples(seg,pose):
            result.append((*pos,*norm,*sh,4.0,
                           math.log(.050),math.log(.036),math.log(.045),*q))
    return result

def ply_bytes(pose,paint):
    rows=gaussian_rows(pose,paint)
    header=("ply\nformat binary_little_endian 1.0\n"
            "comment original source-known two-link object, not trained splats\n"
            f"element vertex {len(rows)}\n"
            +"".join(f"property float {n}\n" for n in FIELDS)
            +"end_header\n").encode("ascii")
    return header+b"".join(struct.pack("<17f",*r) for r in rows)

def ground_truth(pose,paint):
    require(pose,paint)
    return {
        "pose_deg":pose,"paint":paint,"units":"meters",
        "canonical_geometry":{"dimensions_xyz":[LENGTH,WIDTH,HEIGHT],
                              "segments":["upper","lower"],
                              "kinematic_parent":{"upper":None,"lower":"upper"},
                              "hinge_axis_world":[0,1,0],
                              "lower_rest_tip_world":[LENGTH,0,0]},
        "world_vertices":{k:[list(v) for v in vertices(k,pose)] for k in ("upper","lower")},
        "world_centers":{k:list(center(k,pose)) for k in ("upper","lower")},
        "lower_tip_world":list(tip(pose)),
        "colors_rgb":colors(paint),
        "gaussian_count":len(gaussian_rows(pose,paint)),
        "ply_sha256":hashlib.sha256(ply_bytes(pose,paint)).hexdigest(),
        "source_representation":"native mesh + known two-joint rigid rig",
        "splat_representation":"source surface samples, not camera-trained",
    }

def self_test():
    assert math.dist(tip(0),(LENGTH,0,0)) < 1e-10
    assert math.dist(tip(90),(0,0,-LENGTH)) < 1e-10
    assert math.dist(tip(45),(LENGTH/math.sqrt(2),0,-LENGTH/math.sqrt(2)))<1e-10
    for pose,paint in itertools.product(POSES,PAINTS):
        rows=gaussian_rows(pose,paint)
        assert len(rows)==204,len(rows)
        assert all(len(row)==17 and all(math.isfinite(v) for v in row) for row in rows)
        assert all(abs(sum(q*q for q in row[13:17])-1)<1e-10 for row in rows)
        data=ply_bytes(pose,paint)
        assert data==ply_bytes(pose,paint)
        assert len(data.partition(b"end_header\n")[2])==204*17*4
        assert len(vertices("upper",pose))==len(vertices("lower",pose))==8
    assert ply_bytes(0,"base") != ply_bytes(0,"repaint")
    assert ply_bytes(0,"base") != ply_bytes(90,"base")
    for bad in [(-1,"base"),(180,"base"),(0,"missing")]:
        try: ply_bytes(*bad)
        except ValueError: pass
        else: raise AssertionError("invalid action accepted")
    print(json.dumps({"status":"PASS","gaussians_per_pose":204,
                      "vertices_per_pose":16,"tests":"exact hinge/vertices, deterministic ply, nonfinite, unit quaternion, negative edits"}))

if __name__=="__main__":
    self_test()
