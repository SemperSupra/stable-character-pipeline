#!/usr/bin/env python3
"""Build one new original, independently skinned apron on two ORIGINAL synthetic actors.

R009 bounded wardrobe consumer: source #292, existing slots preserved. This is
NOT a physics solver, anatomical or cloth acceptance, licensed costume, or a
private human asset adapter. The actual source GLB bytes must match the real
producer manifest; no fallback to synthetic stubs or guessed skeletons.

Only the new original apron mesh/materials/nodes plus additive manifest metadata
are written in a NEW derived GLB. A separate portable GLB detaches all inactive
mesh/skin node bindings, preserving the complete source authoring mesh library.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import struct
from pathlib import Path
import numpy as np

SCHEMA = "scp.r009.original_apron_reusable_garment.v1"
ACTORS = ("AsterOriginal", "JuniperOriginal")
REQUIRED = ("body", "hair", "top", "bottom", "footwear")
SOURCE_SHA = "470ec8fc159912e8ad2e30733a00c09785e11c1275c26936774690fe2807727b"
MANIFEST_SHA = "3b451c215883fbfe70ac0d81370f6be12cdfad7a55622b390bafe3fab2f664ec"


class GateError(ValueError):
    pass


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_json_strict(raw):
    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise GateError("DUPLICATE_JSON_KEY:" + k)
            out[k] = v
        return out
    def nonfinite(x):
        raise GateError("NONFINITE_JSON:" + x)
    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)
    except (UnicodeError, json.JSONDecodeError, TypeError) as e:
        raise GateError("INVALID_JSON") from e


def read_glb(raw):
    if len(raw) < 28 or raw[:4] != b"glTF":
        raise GateError("NOT_GLB")
    magic, ver, total = struct.unpack_from("<4sII", raw)
    if ver != 2 or total != len(raw):
        raise GateError("GLB_HEADER_OR_LENGTH")
    pos = 12
    chunks = []
    while pos < len(raw):
        if pos + 8 > len(raw):
            raise GateError("TRUNCATED_CHUNK_HEADER")
        n, typ = struct.unpack_from("<I4s", raw, pos)
        pos += 8
        if n % 4 or pos + n > len(raw):
            raise GateError("INVALID_CHUNK_BOUNDARY")
        chunks.append((typ, raw[pos:pos+n]))
        pos += n
    if len(chunks) != 2 or chunks[0][0] != b"JSON" or chunks[1][0] != b"BIN\0":
        raise GateError("GLB_CHUNKS")
    doc = load_json_strict(chunks[0][1].rstrip(b" \t\r\n"))
    if doc.get("asset", {}).get("version") != "2.0" or len(doc.get("buffers", [])) != 1:
        raise GateError("GLTF_SCHEMA")
    if doc["buffers"][0]["byteLength"] > len(chunks[1][1]):
        raise GateError("TRUNCATED_BIN")
    return doc, bytes(chunks[1][1])


def pack_glb(doc, binary):
    b = bytes(binary)
    doc["buffers"][0]["byteLength"] = len(b)
    jb = json.dumps(doc, separators=(",", ":"), sort_keys=True, ensure_ascii=True,
                    allow_nan=False).encode("ascii")
    jb += b" " * ((-len(jb)) % 4)
    b += b"\0" * ((-len(b)) % 4)
    out = bytearray(struct.pack("<4sII", b"glTF", 2, 12+8+len(jb)+8+len(b)))
    for typ, buf in ((b"JSON", jb), (b"BIN\0", b)):
        out.extend(struct.pack("<I4s", len(buf), typ))
        out.extend(buf)
    return bytes(out)


def accessor(doc, binary, index):
    a = doc["accessors"][index]
    v = doc["bufferViews"][a["bufferView"]]
    if v.get("buffer", 0) != 0 or a.get("sparse") or v.get("byteStride"):
        raise GateError("UNSUPPORTED_INTERLEAVED_OR_SPARSE")
    dt = {5121:np.dtype("u1"), 5123:np.dtype("<u2"), 5125:np.dtype("<u4"),
          5126:np.dtype("<f4")}.get(a["componentType"])
    c = {"SCALAR":1, "VEC3":3,"VEC4":4,"MAT4":16}.get(a["type"])
    if dt is None or c is None:
        raise GateError("ACCESSOR_TYPE")
    off = v.get("byteOffset",0)+a.get("byteOffset",0)
    size = a["count"]*dt.itemsize*c
    if off < 0 or off+size > len(binary) or off+size > v.get("byteOffset",0)+v["byteLength"]:
        raise GateError("ACCESSOR_BOUNDS")
    x = np.frombuffer(binary, dtype=dt, count=a["count"]*c, offset=off).reshape(-1,c)
    if x.dtype.kind == "f" and not np.isfinite(x).all():
        raise GateError("NONFINITE_ACCESSOR")
    return x


def append_accessor(doc, binary, vals, component_type, kind, target):
    dt = {5121:np.dtype("u1"), 5125:np.dtype("<u4"), 5126:np.dtype("<f4")}[component_type]
    arr = np.asarray(vals, dtype=dt)
    cc = {"SCALAR":1,"VEC3":3,"VEC4":4}[kind]
    if arr.ndim != 2 or arr.shape[1] != cc or len(arr) == 0:
        raise GateError("APPEND_SHAPE")
    if arr.dtype.kind == "f" and not np.isfinite(arr).all():
        raise GateError("APPEND_NONFINITE")
    while len(binary) % 4:
        binary.append(0)
    off = len(binary)
    raw = arr.tobytes(order="C")
    binary.extend(raw)
    vid = len(doc["bufferViews"])
    doc["bufferViews"].append({"buffer":0,"byteOffset":off,"byteLength":len(raw),"target":target})
    a = {"bufferView":vid,"componentType":component_type,"type":kind,"count":len(arr)}
    if kind == "VEC3" and component_type == 5126 and target == 34962:
        a["min"] = arr.min(axis=0).astype(float).tolist()
        a["max"] = arr.max(axis=0).astype(float).tolist()
    aid = len(doc["accessors"])
    doc["accessors"].append(a)
    return aid


def validate_producer(doc, binary, source_raw, manifest_raw):
    if sha(source_raw) != SOURCE_SHA or sha(manifest_raw) != MANIFEST_SHA:
        raise GateError("SOURCE_EXACT_DIGEST")
    m = load_json_strict(manifest_raw)
    if m.get("schema") != "scp.original_wardrobe_manifest.v1" or m.get("derived_sha256") != sha(source_raw):
        raise GateError("MANIFEST_SOURCE_SHA")
    if doc.get("extras", {}).get("source_class") != "ORIGINAL_SELF_AUTHORED_SYNTHETIC" or m.get("source_class") != "ORIGINAL_SELF_AUTHORED_SYNTHETIC":
        raise GateError("NOT_ORIGINAL_SYNTHETIC")
    if m.get("subjects") != list(ACTORS) or len(doc.get("skins", [])) != 2:
        raise GateError("ACTOR_SOURCE")
    names = {n.get("name"):i for i,n in enumerate(doc.get("nodes",[]))}
    if len(names) != len(doc.get("nodes",[])):
        raise GateError("DUPLICATE_SOURCE_NODE")
    for i, actor in enumerate(ACTORS):
        if len(doc["skins"][i]["joints"]) != 35:
            raise GateError("SOURCE_35_JOINT")
        root = names.get(actor+"_SceneRoot")
        if root is None:
            raise GateError("SOURCE_ROOT")
        slots = m["actor_slots"][actor]
        for s in REQUIRED:
            if s not in slots:
                raise GateError("SOURCE_MISSING_REQUIRED_SLOT")
        for name, entry in slots.items():
            idx = entry["node"]
            if idx >= len(doc["nodes"]):
                raise GateError("SOURCE_SLOT_INDEX")
            node = doc["nodes"][idx]
            if node.get("name") != actor+"_Wardrobe_"+name or node.get("skin") != i or node.get("mesh") != entry["mesh"]:
                raise GateError("SOURCE_SLOT_BIND")
        if len(set(doc["nodes"][root].get("children",[]))) != len(doc["nodes"][root].get("children",[])):
            raise GateError("DUPLICATE_SCENE_CHILD")
    return m, names


def closest_on_tri(p, a, b, c):
    """Ericson point-to-triangle exact closest point, barycentric; rejects degenerate."""
    ab = b-a; ac=c-a
    if np.dot(np.cross(ab,ac),np.cross(ab,ac)) <= 1e-16:
        raise GateError("SOURCE_DEGENERATE_FACE")
    ap=p-a; d1=np.dot(ab,ap); d2=np.dot(ac,ap)
    if d1<=0 and d2<=0:return a,(1.,0.,0.)
    bp=p-b; d3=np.dot(ab,bp); d4=np.dot(ac,bp)
    if d3>=0 and d4<=d3:return b,(0.,1.,0.)
    vc=d1*d4-d3*d2
    if vc<=0 and d1>=0 and d3<=0:
        v=d1/(d1-d3);return a+v*ab,(1-v,v,0.)
    cp=p-c;d5=np.dot(ab,cp);d6=np.dot(ac,cp)
    if d6>=0 and d5<=d6:return c,(0.,0.,1.)
    vb=d5*d2-d1*d6
    if vb<=0 and d2>=0 and d6<=0:
        w=d2/(d2-d6);return a+w*ac,(1-w,0.,w)
    va=d3*d6-d5*d4
    if va<=0 and d4-d3>=0 and d5-d6>=0:
        w=(d4-d3)/((d4-d3)+(d5-d6));return b+w*(c-b),(0.,1-w,w)
    denom=va+vb+vc
    if denom <= 1e-14:raise GateError("SOURCE_NEAR_DEGENERATE")
    v=vb/denom;w=vc/denom
    return a+v*ab+w*ac,(1-v-w,v,w)


def prepare_bottom(doc, binary, entry):
    prims = doc["meshes"][entry["mesh"]]["primitives"]
    if len(prims) != 1:
        raise GateError("EXPECTED_ONE_BOTTOM_PRIMITIVE")
    p=prims[0]
    pos=accessor(doc,binary,p["attributes"]["POSITION"]).astype(np.float64)
    js=accessor(doc,binary,p["attributes"]["JOINTS_0"]).astype(np.int64)
    ws=accessor(doc,binary,p["attributes"]["WEIGHTS_0"]).astype(np.float64)
    fs=accessor(doc,binary,p["indices"]).reshape(-1,3).astype(np.int64)
    if len(pos)<100 or len(fs)<100 or (fs<0).any() or (fs>=len(pos)).any():
        raise GateError("SOURCE_BOTTOM_TOPOLOGY")
    if js.min()<0 or js.max()>=35 or (ws<0).any() or not np.allclose(ws.sum(axis=1),1,atol=2e-4):
        raise GateError("SOURCE_BOTTOM_WEIGHTS")
    # Restrict garment transfer to real source surface near its pelvis/waist, not feet/arms.
    allowed=np.where((pos[fs][:,:,1].mean(axis=1) >= .54)&(pos[fs][:,:,1].mean(axis=1)<=1.025))[0]
    centroids=pos[fs[allowed]].mean(axis=1)
    return pos,js,ws,fs,allowed,centroids


def profile(pos, y):
    x=pos[np.abs(pos[:,1]-y)<.040]
    if len(x)<16:
        raise GateError("INSUFFICIENT_ACTUAL_PROFILE")
    return float(np.quantile(np.abs(x[:,0]),.985)), float(np.quantile(np.abs(x[:,2]),.985))


def pattern_parts(pos):
    """One shared design, measured differently on each original synthetic bottom."""
    # A rounded front apron panel; front is source -Z, not arbitrarily guessed.
    # Side tie strips are part of the same independently removable garment mesh.
    segments=25
    ys=np.linspace(.625,.985,9) # bottom to waist
    rows=[]; normals=[]
    for iy,y in enumerate(ys):
        rx,rz=profile(pos,float(y))
        f=(.985-y)/(.985-.625)
        rx*= (.87+.09*f)
        for k in range(segments):
            theta=-.84+1.68*k/(segments-1)
            # geometric ease independent from protected source
            pad=.034+.012*f
            rows.append(((rx+pad)*math.sin(theta), y, -(rz+pad)*math.cos(theta)))
            n=np.asarray((math.sin(theta),.03*f,-math.cos(theta)),dtype=float)
            n/=np.linalg.norm(n);normals.append(n)
    faces=[]
    for i in range(len(ys)-1):
        for j in range(segments-1):
            a=i*segments+j;b=a+1;c=a+segments;d=c+1
            faces.extend(((a,c,d),(a,d,b))) # outward -Z front
    # separate structural waistband, full waist front and two tie tails
    wb=[]; wn=[]
    for y in (.970,1.020):
        rx,rz=profile(pos,float(min(y,1.015)))
        for k in range(segments):
            theta=-1.05+2.10*k/(segments-1)
            wb.append(((rx+.047)*math.sin(theta),y,-(rz+.047)*math.cos(theta)))
            n=np.asarray((math.sin(theta),0,-math.cos(theta)),dtype=float);wn.append(n)
    wf=[]
    for j in range(segments-1):
        a=j;b=j+1;c=segments+j;d=c+1
        wf.extend(((a,c,d),(a,d,b)))
    return [("apron_panel",np.asarray(rows,dtype=np.float32),np.asarray(normals,dtype=np.float32),np.asarray(faces,dtype=np.uint32),0),
            ("waistband",np.asarray(wb,dtype=np.float32),np.asarray(wn,dtype=np.float32),np.asarray(wf,dtype=np.uint32),1)]


def transfer(pos,js,ws,fs,allowed,centroids,target):
    """Bounded exact nearest-source-triangle barycentric transfer, not anatomical fitting."""
    # Source has 2969 bottom vertices. For each new garment vertex, nearest 48
    # triangle centroids and exact point-to-triangle distances are evaluated.
    from scipy.spatial import cKDTree
    k=min(48,len(centroids))
    tree=cKDTree(centroids)
    local=[];weights=[];distances=[]
    for point in target.astype(np.float64):
        cand=np.atleast_1d(tree.query(point,k=k)[1])
        best=(float('inf'),None,None)
        for q in cand:
            tri=fs[allowed[int(q)]]
            try: near,bary=closest_on_tri(point,*pos[tri])
            except GateError:continue
            dist=float(np.linalg.norm(near-point))
            if dist<best[0]:best=(dist,tri,bary)
        if best[1] is None or best[0]>.18:
            raise GateError("MISSING_LOCAL_BODY_CORRESPONDENCE")
        accum=np.zeros(35,dtype=np.float64)
        for idx,bary in zip(best[1],best[2]):
            for joint,w in zip(js[idx],ws[idx]):
                accum[int(joint)]+=float(bary)*float(w)
        if (accum < -1e-8).any() or not math.isfinite(float(accum.sum())) or accum.sum()<1e-8:
            raise GateError("BAD_TRANSFERRED_WEIGHTS")
        order=np.argsort(-accum,kind='stable')[:4]
        vals=accum[order];vals/=vals.sum()
        if (vals<0).any() or not np.allclose(vals.sum(),1,atol=1e-6):
            raise GateError("BAD_TOP4_NORMALIZATION")
        local.append(order.astype(np.uint8));weights.append(vals.astype(np.float32));distances.append(best[0])
    return np.asarray(local,dtype=np.uint8),np.asarray(weights,dtype=np.float32),distances


def build(raw, mraw):
    doc, raw_bin=read_glb(raw)
    m,names=validate_producer(doc,raw_bin,raw,mraw)
    old_meshes=copy.deepcopy(doc["meshes"])
    old_skins=copy.deepcopy(doc["skins"])
    old_animations=copy.deepcopy(doc.get("animations",[]))
    old_bin_len=len(raw_bin)
    bb=bytearray(raw_bin)
    metrics={}
    for actor_index,actor in enumerate(ACTORS):
        if "apron" in m["actor_slots"][actor]:raise GateError("APRON_SLOT_EXISTS")
        src=m["actor_slots"][actor]["bottom"]
        pos,js,ws,fs,allowed,centroids=prepare_bottom(doc,raw_bin,src)
        parts=pattern_parts(pos)
        materials=[]
        for label,rgba in [("panel",[.94,.91,.85,1.]),("band",[.18,.20,.23,1.])]:
            materials.append(len(doc["materials"]))
            doc["materials"].append({"name":actor+"_original_apron_"+label,
                 "pbrMetallicRoughness":{"baseColorFactor":rgba,"metallicFactor":0.,"roughnessFactor":.92},
                 "doubleSided":True})
        primitives=[];partmetrics={}
        for part_name,vs,ns,faces,material_idx in parts:
            # Triangles must be front-facing along the source negative Z direction.
            norm=np.cross(vs[faces[:,1]]-vs[faces[:,0]],vs[faces[:,2]]-vs[faces[:,0]])
            areas=np.linalg.norm(norm,axis=1)
            if areas.min()<=1e-8 or np.mean(norm[:,2])>=0:
                raise GateError("INVALID_APRON_ORIENTATION")
            j,w,dist=transfer(pos,js,ws,fs,allowed,centroids,vs)
            attrs={"POSITION":append_accessor(doc,bb,vs,5126,"VEC3",34962),
                   "NORMAL":append_accessor(doc,bb,ns,5126,"VEC3",34962),
                   "JOINTS_0":append_accessor(doc,bb,j,5121,"VEC4",34962),
                   "WEIGHTS_0":append_accessor(doc,bb,w,5126,"VEC4",34962)}
            indices=append_accessor(doc,bb,faces.reshape(-1,1),5125,"SCALAR",34963)
            primitives.append({"attributes":attrs,"indices":indices,"material":materials[material_idx],
                               "extras":{"original_piece":part_name,"physics_accepted":False}})
            partmetrics[part_name]={"vertices":len(vs),"triangles":len(faces),
                                    "rest_source_surface_distance_max_m":max(dist),
                                    "rest_source_surface_distance_p95_m":float(np.quantile(dist,.95)),
                                    "min_face_double_area_m2":float(min(areas)),
                                    "skin_weight_error_max":float(max(abs(w.sum(axis=1)-1)))}
        mesh_id=len(doc["meshes"])
        doc["meshes"].append({"name":actor+"_Original_UtilityApron_SeparateSkinnedMesh",
                              "primitives":primitives})
        node_id=len(doc["nodes"])
        doc["nodes"].append({"name":actor+"_Wardrobe_apron","mesh":mesh_id,"skin":actor_index,
                             "extras":{"wardrobe_slot":"apron","actor":actor,"original_garment":True,
                                       "visual_accepted":False,"collision_accepted":False}})
        root=doc["nodes"][names[actor+"_SceneRoot"]]
        root.setdefault("children",[]).append(node_id)
        m["actor_slots"][actor]["apron"]={"node":node_id,"mesh":mesh_id,"skin":actor_index,
                                           "material_ids":materials}
        metrics[actor]=partmetrics
    m["presets"]["original_apron"]=list(REQUIRED)+["apron"]
    m["separate_new_geometry_for_original_apron"]=True
    m["source_original_authoring_sha256"]=sha(raw)
    doc.setdefault("extras",{})["original_apron_research"]={
        "schema":SCHEMA,"parent_source_sha256":sha(raw),"original_garment_design":"generic utility apron",
        "characters":list(ACTORS),"source_mesh_library_preserved":True,
        "cloth_sim_accepted":False,"native_blender_accepted":False,"source_original_synthetic_only":True,
        "public_release_approved":False}
    master=pack_glb(doc,bb)
    m["derived_sha256"]=sha(master)
    # portable consumer: hide inactive mesh/skin node bindings, not just scene children
    pd=copy.deepcopy(doc)
    active={}
    for actor in ACTORS:
        visible=set(m["presets"]["original_apron"])
        root=pd["nodes"][names[actor+"_SceneRoot"]]
        kept=[]
        for slot,entry in m["actor_slots"][actor].items():
            idx=entry["node"]
            if slot in visible:
                if idx not in root["children"]:root["children"].append(idx)
                kept.append(slot)
            else:
                if idx in root["children"]:root["children"].remove(idx)
                pd["nodes"][idx].pop("mesh",None)
                pd["nodes"][idx].pop("skin",None)
        active[actor]=sorted(kept)
    pd["extras"]["original_apron_portable_research"]={
        "schema":SCHEMA+".portable", "master_sha256":sha(master),
        "active_slots":active,"source_mesh_library_preserved":True,
        "native_blender_accepted":False,"full_motion_collision_accepted":False}
    portable=pack_glb(pd,bb)
    # Ensure source derivation never changes original recorded mesh and skin input.
    if doc["meshes"][:len(old_meshes)]!=old_meshes or doc["skins"]!=old_skins or doc.get("animations",[])!=old_animations:
        raise GateError("SOURCE_MESH_SKIN_OR_ANIMATION_CHANGED")
    d2,b2=read_glb(master);d3,b3=read_glb(portable)
    if b2[:old_bin_len]!=raw_bin or b3[:old_bin_len]!=raw_bin:
        raise GateError("ORIGINAL_BINARY_PREFIX_CHANGED")
    if d3["meshes"]!=d2["meshes"] or d3["skins"]!=d2["skins"] or d3.get("animations",[])!=d2.get("animations",[]):
        raise GateError("PORTABLE_LIBRARY_CHANGED")
    return master,portable,m,{"schema":SCHEMA+".receipt","source_sha256":sha(raw),
        "source_manifest_sha256":sha(mraw),"master_sha256":sha(master),"portable_sha256":sha(portable),
        "source_bin_prefix_preserved":True,"original_skin_animation_unchanged":True,
        "original_mesh_library_preserved":True,"actors":metrics,"portable_active_slots":active,
        "new_garment_primitive_count_each":2,"original_36_joints_instead_of_35":False,
        "fully_fitted":False,"collision_accepted":False,"native_blender_accepted":False,
        "physical_cloth_accepted":False,"human_visual_accepted":False,"release_approved":False}


def export(source,manifest,master,portable,new_manifest,receipt):
    paths=[Path(x).resolve() for x in (source,manifest,master,portable,new_manifest,receipt)]
    if len(set(paths))!=len(paths) or any(x.exists() for x in paths[2:]):
        raise GateError("OUTPUT_OVERWRITE_OR_ALIAS")
    raw=Path(source).read_bytes(); mraw=Path(manifest).read_bytes()
    result=build(raw,mraw)
    contents=[result[0],result[1],(json.dumps(result[2],sort_keys=True,indent=2)+"\n").encode(),
              (json.dumps(result[3],sort_keys=True,indent=2)+"\n").encode()]
    for path,content in zip(paths[2:],contents):
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("xb") as f:f.write(content)
    if sha(Path(source).read_bytes())!=sha(raw) or sha(Path(manifest).read_bytes())!=sha(mraw):
        raise GateError("SOURCE_CHANGED_DURING_EXPORT")
    return result[3]


def main():
    p=argparse.ArgumentParser()
    for k in ("source","manifest","master","portable","new-manifest","receipt"):
        p.add_argument("--"+k,required=True)
    a=p.parse_args()
    receipt=export(a.source,a.manifest,a.master,a.portable,a.new_manifest,a.receipt)
    print(json.dumps(receipt,sort_keys=True))

if __name__=="__main__":main()
