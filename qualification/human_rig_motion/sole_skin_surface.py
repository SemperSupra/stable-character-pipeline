#!/usr/bin/env python3
"""Original synthetic human 35-joint GLB skinned footwear-surface screen.

Independently evaluates the exported original footwear vertex attributes,
skin inverse-bind matrices, and all 72 source joint transforms. Source Y=0
is an authored ground-plane hypothesis, NOT measured terrain or contact force.
No human anatomical/collision/photo/CPE acceptance is inferred.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from foot_anchor_support import FRAMES, FPS, node_tracks
from observe import ACTORS, analyze, load_glb, require, values

PLANE_Y=0.0
NEAR_M=.030
BELOW_M=-.004
SLIDE_M_PER_S=.24
SOLE_BAND_M=.025
MAX_FOOTWEAR_VERTICES=10000

def ibm_position(m,p):
    require(len(m)==16 and len(p)==3,"bad inverse bind matrix/vertex")
    require(all(math.isfinite(c) for c in m+p),"nonfinite inverse bind/position")
    x,y,z=p
    v=(m[0]*x+m[4]*y+m[8]*z+m[12],
       m[1]*x+m[5]*y+m[9]*z+m[13],
       m[2]*x+m[6]*y+m[10]*z+m[14])
    w=m[3]*x+m[7]*y+m[11]*z+m[15]
    require(abs(w-1.)<1.e-4,"non-affine inverse bind")
    return v

def deform(p,joints,weights,joint_ids,matrices,world,frame):
    require(len(p)==3 and len(joints)==len(weights)==4,
            "non-original four-influence skin")
    require(all(type(j) is int and 0<=j<len(joint_ids) for j in joints),
            "out-of-range skin joint")
    require(all(math.isfinite(w) and w>=0 for w in weights) and
            abs(sum(weights)-1.)<1.e-4,"invalid skin weights")
    out=[0.,0.,0.]
    for index,w in zip(joints,weights):
        if w<=0:continue
        v=ibm_position(matrices[index],p)
        t,q=world(joint_ids[index],frame)
        # qrotate is the same independently hostile-tested glTF node algebra
        # used by the original human foot-anchor observer.
        from foot_anchor_support import qrotate
        transformed=qrotate(q,v)
        for k in range(3):out[k]+=w*(t[k]+transformed[k])
    require(all(math.isfinite(x) for x in out),"nonfinite skinned foot vertex")
    return tuple(out)

def inspect(raw):
    structure=analyze(raw)
    doc,binary=load_glb(raw)
    world=node_tracks(doc,binary)
    nodes=doc["nodes"]
    names={n.get("name"):i for i,n in enumerate(nodes)}
    output={}
    for ai,actor in enumerate(ACTORS):
        node=nodes[names[actor+"_Wardrobe_footwear"]]
        require(node.get("skin")==ai and not any(
            k in node for k in ("matrix","rotation","translation","scale")),
            "footwear node has unsupported skin or transform")
        skin=doc["skins"][ai]
        joints=skin["joints"]
        matrices=values(doc,binary,skin["inverseBindMatrices"])
        require(len(joints)==len(matrices)==35,"wrong 35-bone skin")
        prims=doc["meshes"][node["mesh"]]["primitives"]
        # Each source footwear vertex is sampled ONCE in its bind pose and
        # source side. Only the bottom fixed band represents the sole.
        by_side={"L":[],"R":[]}
        count=0
        for prim in prims:
            attrs=prim["attributes"]
            points=values(doc,binary,attrs["POSITION"])
            ji=values(doc,binary,attrs["JOINTS_0"])
            weights=values(doc,binary,attrs["WEIGHTS_0"])
            require(len(points)==len(ji)==len(weights),"footwear skin mismatch")
            count+=len(points)
            require(count<=MAX_FOOTWEAR_VERTICES,"footwear vertex budget exceeded")
            for i,(p,j,w) in enumerate(zip(points,ji,weights)):
                require(len(p)==3 and all(math.isfinite(x) for x in p),
                        "invalid source foot position")
                # Original producer has X-left and X-right shoe locations.
                # Midline shoe vertices are ambiguity, not reclassified.
                if p[0]<-.01:by_side["L"].append((p,j,w))
                elif p[0]>.01:by_side["R"].append((p,j,w))
        side_receipts={}
        for side,verts in by_side.items():
            require(len(verts)>=20,"missing original footwear half "+side)
            low=min(v[0][1] for v in verts)
            sole=[v for v in verts if v[0][1]<=low+SOLE_BAND_M]
            require(len(sole)>=2,"too few bound original sole vertices")
            min_y=[];footprints=[]
            for frame in range(FRAMES):
                deformed=[deform(*v,joints,matrices,world,frame) for v in sole]
                low_i=min(range(len(deformed)),key=lambda i:deformed[i][1])
                min_y.append(deformed[low_i][1])
                footprints.append(deformed[low_i])
            near=[y<=PLANE_Y+NEAR_M for y in min_y]
            crossing=[f for f in range(FRAMES) if min_y[f]<PLANE_Y+BELOW_M]
            steps=[f for f in range(FRAMES-1) if near[f] and near[f+1]]
            distances=[math.hypot(footprints[f+1][0]-footprints[f][0],
                                  footprints[f+1][2]-footprints[f][2])
                       for f in steps]
            slides=[f for f,d in zip(steps,distances) if d*FPS>SLIDE_M_PER_S]
            side_receipts[side]={
                "source_footwear_vertices":len(verts),
                "fixed_bind_sole_vertices":len(sole),
                "bind_min_y_m":round(low,6),
                "world_sole_min_y_m":round(min(min_y),6),
                "world_sole_max_y_m":round(max(min_y),6),
                "frames_below_authored_plane_minus_4mm":crossing,
                "near_plane_adjacent_frame_pairs":len(steps),
                "potential_contact_point_switch_or_skate_frames":slides,
                "max_source_sole_proxy_horizontal_m_per_s":
                  round(max((d*FPS for d in distances),default=0.),6),
                "support_basis":"minimum evaluated fixed bind-sole band vertex",
                "limits":"closest vertex may switch, not measured force/contact"}
        output[actor]=side_receipts
    return {
        "schema":"scp.r009.original_synthetic_footwear_skin_surface.v1",
        "source_glb_sha256":hashlib.sha256(raw).hexdigest(),
        "independent_structure_sha256":structure["sha256"],
        "source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
        "actors":output,"frames":FRAMES,"fps":FPS,
        "ground_plane_y_m":PLANE_Y,
        "ground_plane_basis":"author-assumed world Y=0, NOT independent terrain",
        "contact_sliding":"PROXY_ONLY, NOT_FORCE_OR_PHYSICAL_CONTACT",
        "human_anatomical_JCS":"NOT_PROVEN",
        "garment_body_triangle_BVH":"NOT_RUN",
        "photo_identity_fit":"NOT_RUN",
        "release_or_CPE_admission":False,
        "human_gait_accepted":False,"model_mutation":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--glb",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    dest=Path(a.out)
    require(not dest.exists(),"refuse overwrite evidence")
    raw=Path(a.glb).read_bytes()
    require(len(raw)<=64*1024*1024,"source over budget")
    report=inspect(raw)
    dest.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("FOOTWEAR_SURFACE_SCREEN_NO_PHYSICAL_GAIT_ACCEPTANCE",report["source_glb_sha256"])

if __name__=="__main__":
    main()
