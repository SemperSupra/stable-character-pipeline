#!/usr/bin/env python3
"""Opt-in original-only R009 torso continuity and genuinely different outfit cuts.

Derives from the frozen v1 wardrobe source. No downloaded model or protected
identity. Keeps the v1 actor/skin/node/slot contract and source bytes unchanged.
A continuous torso-neck-head surface is NOT a watertight full human body.
"""
import argparse
import hashlib
import json
import math
import struct
import tempfile
from pathlib import Path

import humanization_v2 as h
import modular_wardrobe_v1 as v1
from phase_gait35 import animate
from rig35_v2 import main_expand, glb_pack
from verify_original_glb import decode, accessory

# Short, bounded anatomical garment transition patch. This joins the torso
# silhouette and sleeve-root silhouette by OVERLAP only, not by a shared
# watertight edge. Human visual acceptance and cloth physics remain UNKNOWN.
SHOULDER_GUSSET_RINGS = (
    # |x|, vertical_radius, depth_radius, torso/chest_skin_weight
    (.119, .064, .084, .88),
    (.155, .077, .093, .76),
    (.198, .080, .092, .54),
    (.231, .074, .083, .30),
    (.271, .059, .068, .12),
)
SHOULDER_GUSSET_SIDES = 32

def attach_shoulder_gussets_original(g,which):
    """Two source-original curved sleeve-root transition bands.

    They overlap the continuous jacket torso and shoulder sleeves without
    editing the parent original source mesh/rig. Weights blend chest to the
    source-original shoulder role, preserving source skeleton cardinality.
    """
    material="coralJacket" if which==0 else "tealJacket"
    part=g.part(material)
    made={}
    for sign,side in ((-1,"L"),(1,"R")):
        base=len(part["p"])//3
        for cx,vertical,depth,chest_weight in SHOULDER_GUSSET_RINGS:
            for i in range(SHOULDER_GUSSET_SIDES):
                phi=math.tau*i/SHOULDER_GUSSET_SIDES
                cs,ss=math.cos(phi),math.sin(phi)
                part["p"].extend([sign*cx,1.345+vertical*cs,depth*ss])
                normal=h.v1.unit((0.,cs/vertical,ss/depth))
                part["n"].extend(normal)
                part["j"].extend([h.v1.JIDX["chest"],
                                  h.v1.JIDX["shoulder_"+side],0,0])
                part["w"].extend([chest_weight,1.-chest_weight,0.,0.])
        for k in range(len(SHOULDER_GUSSET_RINGS)-1):
            for j in range(SHOULDER_GUSSET_SIDES):
                a=base+k*SHOULDER_GUSSET_SIDES+j
                b=base+k*SHOULDER_GUSSET_SIDES+(j+1)%SHOULDER_GUSSET_SIDES
                c=a+SHOULDER_GUSSET_SIDES
                d=b+SHOULDER_GUSSET_SIDES
                if sign>0:
                    part["i"].extend([a,b,c,b,d,c])
                else:
                    part["i"].extend([a,c,b,b,c,d])
        made[side]={"added_vertices":len(SHOULDER_GUSSET_RINGS)*SHOULDER_GUSSET_SIDES,
                    "added_triangles":2*(len(SHOULDER_GUSSET_RINGS)-1)*SHOULDER_GUSSET_SIDES,
                    "weight_roles":["chest","shoulder_"+side]}
    return made

def trouser_hip_inset(material,start,end,radius,bone_a,bone_b):
    """Move only the original two pant thigh tube starts inside the waist yoke."""
    if (material not in ("slatePants","ochrePants")
        or not bone_a.startswith("hip_")
        or bone_b!="knee_"+bone_a.removeprefix("hip_")):
        return tuple(start),radius,False
    # First .24 setback exposed unclothed skin at the pelvis; visually RED.
    # Retain a small 7.5% inset so the thigh shell remains under the coat hem.
    fraction=.075
    moved=tuple(a+fraction*(b-a) for a,b in zip(start,end))
    return moved,min(radius,.110),True

def knee_cap_to_source_joint(material,center,radii,bone):
    """Align only original pant kneecap ellipsoids with 17-joint rest centers.

    Source original had y=.340 while the actual knee joint is y=.490 m,
    generating visible gaps between upper and lower skinned pant tubes.
    """
    if (material not in ("slatePants","ochrePants")
        or bone not in ("knee_L","knee_R")
        or abs(center[1]-.340)>1e-6):
        return tuple(center),tuple(radii),False
    xyz=h.v1.POS[bone]
    return tuple(xyz),(.078,.086,.076),True

def join_original_trouser_segments(g,material,upper,lower):
    """One indexed pant-leg tube crossing the true knee joint.

    This replaces two independent open-ended upper/lower trouser tubes with
    ONE source-original manifold tube (open only at hip and ankle).
    It does NOT seal the torso, ankle, other clothes, or whole human body.
    Shape, vertex weights and normals are authored from source joint positions.
    """
    if material not in ("slatePants","ochrePants"):
        raise ValueError("JOINED_TROUSER_MATERIAL_NOT_ORIGINAL")
    start,knee,r0,r1,hip_role,knee_role,steps,sides=upper
    lower_knee,ankle,s0,s1,lower_knee_role,ankle_role,lower_steps,lower_sides=lower
    if (tuple(knee)!=tuple(lower_knee) or knee_role!=lower_knee_role
        or knee_role!="knee_"+hip_role.removeprefix("hip_")
        or ankle_role!="ankle_"+hip_role.removeprefix("hip_")
        or steps!=lower_steps or sides!=lower_sides
        or steps<3 or sides<8
        or any(not math.isfinite(v) for p in (start,knee,ankle) for v in p)
        or min(r0,r1,s0,s1)<=0):
        raise ValueError("JOINED_TROUSER_SOURCE_SEAM_MISMATCH")
    # Both formerly separate ring ends now use one shared knee ring, with
    # a smoothly averaged radius and 100% source-knee skin influence.
    knee_radius=(r1+s0)*.5
    centers=[]
    radii=[]
    for k in range(steps+1):
        t=k/steps
        centers.append(tuple((1-t)*a+t*b for a,b in zip(start,knee)))
        radii.append((1-t)*r0+t*knee_radius)
    for k in range(1,steps+1):
        t=k/steps
        centers.append(tuple((1-t)*a+t*b for a,b in zip(knee,ankle)))
        radii.append((1-t)*knee_radius+t*s1)
    part=g.part(material)
    offset=len(part["p"])//3
    joints=[(hip_role,knee_role),(knee_role,ankle_role)]
    for ri,(center,radius) in enumerate(zip(centers,radii)):
        prev=centers[max(ri-1,0)]
        nxt=centers[min(ri+1,len(centers)-1)]
        tangent=h.v1.unit(h.v1.sub(nxt,prev))
        ref=(0.,0.,1.) if abs(tangent[2])<.85 else (0.,1.,0.)
        u=h.v1.unit(h.v1.cross(tangent,ref))
        v=h.v1.unit(h.v1.cross(tangent,u))
        if ri<=steps:
            role0,role1=joints[0]
            alpha=ri/steps
        else:
            role0,role1=joints[1]
            alpha=(ri-steps)/steps
        for sidei in range(sides):
            phi=math.tau*sidei/sides
            direction=tuple(u[j]*math.cos(phi)+v[j]*math.sin(phi) for j in range(3))
            xyz=tuple(center[j]+radius*direction[j] for j in range(3))
            part["p"].extend(xyz)
            part["n"].extend(direction)
            part["j"].extend((h.v1.JIDX[role0],h.v1.JIDX[role1],0,0))
            part["w"].extend((1-alpha,alpha,0.,0.))
    for ring in range(2*steps):
        for sector in range(sides):
            a=offset+ring*sides+sector
            b=offset+ring*sides+(sector+1)%sides
            c=a+sides
            d=b+sides
            part["i"].extend((a,b,c,b,d,c))
    return {
        "source_original_only":True,
        "joint_knee_ring_index":offset+steps*sides,
        "first_vertex_index":offset,
        "rings":2*steps+1,
        "sides":sides,
        "vertices":(2*steps+1)*sides,
        "triangles":4*steps*sides,
        "watertight_at_knee":True,
        "open_at_pelvis_and_ankle":True,
        "whole_body_watertight":False,
        "garment_collision_accepted":False,
    }

def continuous_figure(which):
    """Replace independent torso and face lofts by one weighted trunk/head loft.

    Hands/limbs remain inherited overlapping surfaces pending full retopology.
    Preserve parent clothing, face decorations, hair, armature and source names.
    """
    original = h.loft_anatomy
    original_tube=h.v1.Geometry.tube
    original_ellipsoid=h.v1.Geometry.ellipsoid
    lower_counts={"inset_hip_tubes":0,"joint_aligned_kneecaps":0}
    leg_segments={side:{} for side in ("L","R")}
    def bounded_tube(self,material,start,end,r0,r1,bone_a,bone_b,steps=10,sides=18,ellipse=(1.,1.)):
        start,r0,changed=trouser_hip_inset(material,start,end,r0,bone_a,bone_b)
        if changed:lower_counts["inset_hip_tubes"]+=1
        # Intercept only source-original trouser legs. The body underlayer,
        # sleeves, and original figure modules are not changed.
        is_upper=(material in ("slatePants","ochrePants")
                  and bone_a in ("hip_L","hip_R")
                  and bone_b=="knee_"+bone_a.removeprefix("hip_"))
        is_lower=(material in ("slatePants","ochrePants")
                  and bone_a in ("knee_L","knee_R")
                  and bone_b=="ankle_"+bone_a.removeprefix("knee_"))
        if is_upper or is_lower:
            side=bone_a.rsplit("_",1)[1]
            key="upper" if is_upper else "lower"
            if key in leg_segments[side]:
                raise ValueError("DUPLICATED_PANT_SEGMENT_"+key+"_"+side)
            if ellipse!=(1.,1.):
                raise ValueError("UNSUPPORTED_ORIGINAL_PANTS_ELLIPSE")
            leg_segments[side][key]=(tuple(start),tuple(end),r0,r1,
                                     bone_a,bone_b,steps,sides)
            return None
        return original_tube(self,material,start,end,r0,r1,bone_a,bone_b,
                             steps=steps,sides=sides,ellipse=ellipse)
    def aligned_ellipsoid(self,material,center,radii,bone,lat=14,lon=20):
        center,radii,changed=knee_cap_to_source_joint(material,center,radii,bone)
        if changed:lower_counts["joint_aligned_kneecaps"]+=1
        return original_ellipsoid(self,material,center,radii,bone,lat=lat,lon=lon)
    skin = "skinWarm" if which == 0 else "skinCool"
    counts = {"head_removed": 0, "trunk_replaced": 0}
    def intercept(g, mat, rings, bones, sides=32):
        lo, hi = rings[0][0], rings[-1][0]
        if mat == skin and lo > 1.4 and hi > 1.7:
            counts["head_removed"] += 1
            return  # replaced by a contiguous trunk-to-cranium loft
        if mat == skin and lo < .9 and 1.40 < hi < 1.5:
            counts["trunk_replaced"] += 1
            merged = list(rings)
            # The trunk's terminal radius connects directly to neck/head.
            # Radial order and ring indexing stay continuous at every level.
            merged.extend([
                (1.480,-.003,.052,.054),
                (1.500,-.008,.053,.054),
                (1.519,-.013,.060,.060),
                (1.548,-.013,.072,.072),
                (1.574,-.010,.081,.083),
                (1.611,0,.091 if which==0 else .088,.095),
                (1.657,0,.102 if which==0 else .096,.105),
                (1.701,.008,.102 if which==0 else .097,.106),
                (1.737,.019,.085,.093),
                (1.766,.025,.052,.062),
                (1.785,.028,.005,.010)])
            def spine_to_head(y):
                if y <= 1.38:
                    return bones(y)
                if y <= 1.48:
                    blend=max(0.,min(1.,(1.48-y)/.10))
                    return ("chest","neck",blend)
                blend=max(0.,min(1.,(1.56-y)/.08))
                return ("neck","head",blend)
            return original(g,mat,merged,spine_to_head,sides=36)
        return original(g,mat,rings,bones,sides=sides)
    try:
        h.loft_anatomy = intercept
        h.v1.Geometry.tube=bounded_tube
        h.v1.Geometry.ellipsoid=aligned_ellipsoid
        geo = v1.adult_body_geometry(which)
        # The original figure had TWO unrelated open-ended pant tubes per
        # leg. Replace them with one shared indexed knee ring, per side.
        pants="slatePants" if which==0 else "ochrePants"
        joined={}
        for side in ("L","R"):
            if set(leg_segments[side])!={"upper","lower"}:
                raise ValueError("INCOMPLETE_JOINED_PANT_SOURCE_"+side)
            upper=leg_segments[side]["upper"]
            lower=leg_segments[side]["lower"]
            merged_upper=(upper[0],upper[1],upper[2],upper[3],
                          upper[4],upper[5],upper[6],upper[7])
            merged_lower=(lower[0],lower[1],lower[2],lower[3],
                          lower[4],lower[5],lower[6],lower[7])
            joined[side]=join_original_trouser_segments(
                geo,pants,merged_upper,merged_lower)
        gussets=attach_shoulder_gussets_original(geo,which)
    finally:
        h.loft_anatomy = original
        h.v1.Geometry.tube=original_tube
        h.v1.Geometry.ellipsoid=original_ellipsoid
    if counts != {"head_removed":1,"trunk_replaced":1}:
        raise ValueError("TOPOLOGY_REPLACEMENT_UNEXPECTED:"+str(counts))
    if set(gussets)!={"L","R"} or any(
        x["added_vertices"]!=160 or x["added_triangles"]!=256
        for x in gussets.values()):
        raise ValueError("SOURCE_SHOULDER_BRIDGE_INCOMPLETE")
    if lower_counts!={"inset_hip_tubes":2,"joint_aligned_kneecaps":2}:
        raise ValueError("SOURCE_PANTS_HIP_KNEE_CORRECTION_INCOMPLETE:"+str(lower_counts))
    if any(not joined[side]["watertight_at_knee"] or
           joined[side]["whole_body_watertight"] or
           joined[side]["rings"]!=2*18+1
           for side in ("L","R")):
        raise ValueError("KNEE_INDEXED_RING_INCOMPLETE")
    return geo

def _append(d, binary, values, kind, fmt, count, target=None):
    while len(binary) % 4: binary.append(0)
    offset=len(binary)
    binary.extend(struct.pack("<"+fmt*len(values),*values))
    view={"buffer":0,"byteOffset":offset,"byteLength":struct.calcsize(fmt)*len(values)}
    if target: view["target"]=target
    view_id=len(d["bufferViews"])
    d["bufferViews"].append(view)
    acc_id=len(d["accessors"])
    d["accessors"].append({"bufferView":view_id,"componentType":{"B":5121,"I":5125,"f":5126}[fmt],
        "count":count,"type":kind})
    return acc_id

def _rings(skin_index, names, rings, sides=28):
    """Surface of revolution with per-ring two-bone skin blend."""
    vertices=[]; normals=[]; joints=[]; weights=[]; indices=[]
    for k,(cy,cx,cz,rx,rz,role0,role1,blend) in enumerate(rings):
        if not (rx>0 and rz>0 and 0<=blend<=1):
            raise ValueError("INVALID_CUT_RING")
        if k and cy<=rings[k-1][0]:
            raise ValueError("NONMONOTONIC_CUT")
        for j in range(sides):
            angle=math.tau*j/sides
            co,si=math.cos(angle),math.sin(angle)
            vertices.extend((cx+rx*co,cy,cz+rz*si))
            nx,nz=co/rx,si/rz
            nn=math.hypot(nx,nz)
            normals.extend((nx/nn,0,nz/nn))
            joints.extend((skin_index[role0],skin_index[role1],0,0))
            weights.extend((blend,1-blend,0,0))
    for k in range(len(rings)-1):
        for j in range(sides):
            a=k*sides+j;b=k*sides+(j+1)%sides
            indices.extend((a,a+sides,b,b,a+sides,b+sides))
    return vertices,normals,joints,weights,indices

def _combine(*surfaces):
    out=[[],[],[],[],[]]
    for surface in surfaces:
        count=len(out[0])//3
        for idx,values in enumerate(surface):
            out[idx].extend((v+count for v in values) if idx==4 else values)
    return out

def _mesh_primitive(d,b,mesh,material,geom):
    pos,nor,joints,weights,indices=geom
    n=len(pos)//3
    if not (n>0 and len(nor)==3*n and len(joints)==4*n
            and len(weights)==4*n and len(indices)%3==0):
        raise ValueError("CUT_VERTEX_FORMAT")
    for i in range(n):
        if any(j>=35 for j in joints[4*i:4*i+4]):
            raise ValueError("CUT_INVALID_JOINT")
        if abs(sum(weights[4*i:4*i+4])-1)>1e-6:
            raise ValueError("CUT_BAD_WEIGHT")
    attrs={
      "POSITION":_append(d,b,pos,"VEC3","f",n,34962),
      "NORMAL":_append(d,b,nor,"VEC3","f",n,34962),
      "JOINTS_0":_append(d,b,joints,"VEC4","B",n,34962),
      "WEIGHTS_0":_append(d,b,weights,"VEC4","f",n,34962)}
    idx=_append(d,b,indices,"SCALAR","I",len(indices),34963)
    d["meshes"][mesh]["primitives"]=[{"attributes":attrs,"indices":idx,"material":material}]

def distinct_cuts(master_path,manifest_path):
    """Create new meshes for sleeveless cropped top and flared cropped trousers."""
    src=Path(master_path).read_bytes()
    d,b0=decode(src);b=bytearray(b0)
    m=json.loads(Path(manifest_path).read_text())
    if m.get("derived_sha256")!=hashlib.sha256(src).hexdigest():
        raise ValueError("MANIFEST_SOURCE_MISMATCH")
    if d.get("extras",{}).get("wardrobe_contract",{}).get("schema")!="scp.original_wardrobe.v1":
        raise ValueError("WARDROBE_CONTRACT_CHANGED")
    for actor in v1.ACTORS:
        skin_id=v1.ACTORS.index(actor)
        skin_nodes=d["skins"][skin_id]["joints"]
        skinidx={d["nodes"][idx]["name"].removeprefix(actor+"_"):j
                 for j,idx in enumerate(skin_nodes)}
        slots=m["actor_slots"][actor]
        # A cropped sleeveless vest/tunic: neither a recolored jacket nor a
        # clone of its sleeve primitives. Independent ring topology.
        top_rings=[]
        for y,rx,rz in ((1.045,.160,.135),(1.085,.163,.139),
                        (1.190,.192,.156),(1.298,.211,.160),
                        (1.365,.189,.144),(1.415,.092,.091)):
            t=max(0.,min(1.,(1.38-y)/.27))
            top_rings.append((y,0,0,rx,rz,"spine","chest",t))
        top=_rings(skinidx,actor,top_rings,32)
        # Separate flared, calf-length culotte cut: distinctive wide cuffs.
        upper=[(.745,0,0,.205,.153,"pelvis","spine",1.),
               (.855,0,0,.209,.153,"pelvis","spine",.85),
               (.960,0,0,.175,.138,"pelvis","spine",.4),
               (1.030,0,0,.167,.128,"pelvis","spine",.1)]
        surfaces=[_rings(skinidx,actor,upper,32)]
        for side,sign in (("L",-1),("R",1)):
            leg=[(.195,sign*.14,0,.137,.119,"ankle_"+side,"knee_"+side,.93),
                 (.290,sign*.14,0,.145,.132,"knee_"+side,"hip_"+side,.82),
                 (.475,sign*.14,0,.143,.132,"knee_"+side,"hip_"+side,.55),
                 (.630,sign*.14,0,.135,.122,"hip_"+side,"knee_"+side,.87),
                 (.820,sign*.14,0,.130,.120,"hip_"+side,"pelvis",.83)]
            surfaces.append(_rings(skinidx,actor,leg,32))
        bottom=_combine(*surfaces)
        for slot,shape in (("alt_top",top),("alt_bottom",bottom)):
            meta=slots[slot]
            prim=d["meshes"][meta["mesh"]]["primitives"][0]
            material=prim["material"]  # exact owner-original colorway
            _mesh_primitive(d,b,meta["mesh"],material,shape)
            meta["material_ids"]=[material]
        m.setdefault("cut_styles",{})[actor]={
           "alt_top":"cropped_sleeveless_vest_v2",
           "alt_bottom":"flared_calf_length_culottes_v2"}
    d["extras"]["wardrobe_contract"]["source_shoulder_transition"]="CHEST_SHOULDER_WEIGHTED_OVERLAPPING_GUSSETS_V2_NOT_WATERTIGHT"
    d["extras"]["wardrobe_contract"]["source_knee_transition"]="KNEE_ELLIPSOIDS_ALIGNED_TO_REST_JOINTS_NOT_WATERTIGHT"
    d["extras"]["wardrobe_contract"]["original_pant_leg_topology"]="SINGLE_INDEXED_37_RING_KNEE_CONNECTED_OPEN_PELVIS_ANKLE"
    d["extras"]["wardrobe_contract"]["source_thigh_tubes"]="STARTS_INSET_UNDER_PELVIS_WAIST_YOKE"
    d["extras"]["wardrobe_contract"]["cut_profile"]="ORIGINAL_DIFFERENT_TOPOLOGY_V2_RESEARCH"
    d["extras"]["wardrobe_contract"]["human_cloth_acceptance"]="UNKNOWN"
    result=glb_pack(d,b)
    Path(master_path).write_bytes(result)
    m["derived_sha256"]=hashlib.sha256(result).hexdigest()
    m["separate_new_geometry_for_alternate"]=True
    m["alternate_differences"]="new independent short sleeveless vest and flared cropped culotte mesh topology"
    m["human_appearance_accepted"]=False
    m["cloth_collision_qualified"]=False
    Path(manifest_path).write_text(json.dumps(m,sort_keys=True,indent=2)+"\n")
    return m

def build(out,manifest):
    paths=[Path(out).resolve(),Path(manifest).resolve()]
    if paths[0]==paths[1]:raise ValueError("OUTPUT_PATH_COLLISION")
    for p in paths:
        if p.exists():raise ValueError("IMMUTABLE_OUTPUT_EXISTS:"+str(p))
    paths[0].parent.mkdir(parents=True,exist_ok=True)
    paths[1].parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        source,rig,gait=(td/name for name in ("body17.glb","body35.glb","gait35.glb"))
        old=h.v1.figure_geometry
        try:
            h.v1.figure_geometry=continuous_figure
            h.v1.make_demo(source)
        finally:
            h.v1.figure_geometry=old
        main_expand(source,rig)
        animate(rig,gait)
        v1.split_skinned_layers(gait,out,manifest)
        m=distinct_cuts(out,manifest)
    return {"schema":"scp.r009.original_wardrobe_refinement.v2",
            "source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
            "derived_sha256":m["derived_sha256"],
            "contiguous_trunk_neck_head_loft":True,
            "weighted_shoulder_sleeve_root_gussets":True,
            "trouser_upper_thigh_tube_starts_inset":True,
            "original_source_kneecaps_aligned_to_joint_rest":True,
            "original_pant_legs_continuous_indexed_through_knee":True,
            "original_waist_pant_leg_seam_closed":False,
            "shoulder_or_body_watertight":False,
            "full_body_watertight":False,
            "new_alt_topology":True,
            "scientific_acceptance":"UNKNOWN_NOT_QUALIFIED",
            "rights_release_merge_cpe_held":True}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--receipt",required=True)
    a=p.parse_args()
    if Path(a.receipt).resolve() in (Path(a.out).resolve(),Path(a.manifest).resolve()):
        p.error("receipt must be distinct from source artifacts")
    r=build(a.out,a.manifest)
    Path(a.receipt).write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    print(json.dumps(r,sort_keys=True))
