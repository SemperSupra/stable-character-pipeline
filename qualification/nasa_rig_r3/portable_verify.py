#!/usr/bin/env python3
"""Independent CPU glTF-2 subset evaluator for R3. No Blender/native 3D claims.

Reads the actual Go-exported GLB, evaluates its skin transforms from glTF
bufferView/accessor/skin/animation objects, rasterizes deformed triangles and
produces source-bound JSON. Fails closed on unsupported transforms/formats.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from PIL import Image, ImageDraw

FORMATS = {5126: ("f", 4), 5123: ("H", 2), 5125: ("I", 4)}
LENGTHS = {"SCALAR": 1, "VEC3": 3, "VEC4": 4, "MAT4": 16}

def finite_vec(v):
    return all(math.isfinite(float(x)) for x in v)

def read_glb(raw):
    if len(raw) < 28 or raw[:4] != b"glTF":
        raise ValueError("bad glTF magic")
    ver, total = struct.unpack_from("<II", raw, 4)
    if ver != 2 or total != len(raw):
        raise ValueError("invalid GLB version/length")
    jlength, jtype = struct.unpack_from("<II", raw, 12)
    if jtype != 0x4E4F534A or jlength <= 0 or 20 + jlength + 8 > len(raw):
        raise ValueError("invalid JSON chunk")
    blob = json.loads(raw[20:20 + jlength])
    pos = 20 + jlength
    binlen, bintype = struct.unpack_from("<II", raw, pos)
    if bintype != 0x004E4942 or pos + 8 + binlen != len(raw):
        raise ValueError("invalid BIN chunk")
    data = raw[pos+8:]
    if blob.get("asset", {}).get("version") != "2.0":
        raise ValueError("not glTF 2.0")
    return blob, data

def accessor(doc, data, i):
    a = doc["accessors"][i]
    if a.get("sparse") or a.get("normalized") or "bufferView" not in a:
        raise ValueError("unsupported accessor layout")
    view = doc["bufferViews"][a["bufferView"]]
    if view.get("buffer") != 0:
        raise ValueError("unexpected external buffer")
    fmt, width = FORMATS[a["componentType"]]
    elements = LENGTHS[a["type"]]
    stride = width * elements
    if view.get("byteStride", stride) != stride:
        raise ValueError("interleaved accessor unsupported")
    start = view.get("byteOffset", 0) + a.get("byteOffset", 0)
    end = start + stride * a["count"]
    if start < 0 or end > len(data) or end > view.get("byteOffset",0)+view["byteLength"]:
        raise ValueError("accessor exceeds bounds")
    out = []
    for k in range(a["count"]):
        vec = struct.unpack_from("<" + fmt * elements, data, start + k*stride)
        if not finite_vec(vec):
            raise ValueError("nonfinite accessor")
        out.append(vec)
    return out

def evaluate(doc, data, manifest, out):
    nodes = doc["nodes"]
    skins = doc["skins"]
    animations = doc["animations"]
    if len(skins) != 1 or len(animations) != 1:
        raise ValueError("expected exactly one skin and animation")
    skin = skins[0]
    js = skin["joints"]
    if len(js) != 33 or len(set(js)) != 33:
        raise ValueError("invalid 33 joint skin")
    ibm = accessor(doc, data, skin["inverseBindMatrices"])
    if len(ibm) != 33:
        raise ValueError("wrong inverse bind matrices count")
    mesh = doc["meshes"][0]["primitives"][0]
    attrs = mesh["attributes"]
    pos = accessor(doc,data,attrs["POSITION"])
    joints = accessor(doc,data,attrs["JOINTS_0"])
    weights = accessor(doc,data,attrs["WEIGHTS_0"])
    indices = accessor(doc,data,mesh["indices"])
    if not (len(pos)==len(joints)==len(weights)>0) or len(indices)%3:
        raise ValueError("skin index/vertex count mismatch")
    for p in weights:
        if abs(sum(p)-1) > 1e-5 or min(p) < 0:
            raise ValueError("invalid normalized skin weights")
    parents = {}
    for idx, node in enumerate(nodes):
        if node.get("rotation") is not None or node.get("scale") is not None or node.get("matrix") is not None:
            raise ValueError("unsupported non-translation transform")
        for child in node.get("children", []):
            if child in parents:
                raise ValueError("node has multiple parents")
            parents[child] = idx

    count = manifest["glb_sample_count"]
    if not 2 <= count <= 30:
        raise ValueError("bounded sequence length")
    translations = {}
    animation = animations[0]
    for channel in animation["channels"]:
        node = channel["target"]["node"]
        if channel["target"]["path"] != "translation" or node in translations:
            raise ValueError("unsupported or duplicate animation channel")
        sampler = animation["samplers"][channel["sampler"]]
        times = accessor(doc,data,sampler["input"])
        values = accessor(doc,data,sampler["output"])
        if len(times)!=count or len(values)!=count or any(abs(t[0]-i)>1e-5 for i,t in enumerate(times)):
            raise ValueError("unbound animation clock or frame gap")
        translations[node] = values
    if len(translations)!=33:
        raise ValueError("not all landmark nodes animated")
    reference = [tuple(node.get("translation",[0,0,0])) for node in nodes]
    for j in js:
        if j not in translations:
            raise ValueError("unanimated joint")

    def world_translations(k):
        found = {}
        def t_for(node, stack):
            if node in found:
                return found[node]
            if node in stack:
                raise ValueError("node hierarchy cycle")
            local = translations[node][k] if node in translations else reference[node]
            base = t_for(parents[node], stack | {node}) if node in parents else (0,0,0)
            out_vec = tuple(base[a]+local[a] for a in range(3))
            found[node] = out_vec
            return out_vec
        return [t_for(i,set()) for i in range(len(nodes))]

    out.mkdir(parents=True, exist_ok=True)
    first, last = None,None
    for k in range(count):
        worlds = world_translations(k)
        deformed=[]
        for v, j, w in zip(pos,joints,weights):
            x=y=z=0.0
            for slot, weight in enumerate(w):
                if weight <= 0: continue
                jid = j[slot]
                if jid >= len(js):
                    raise ValueError("skin joint out of bounds")
                rest = ibm[jid]
                # Only affine identity-rotation inverse bind matrices are supported.
                ideal = (1,0,0,0,0,1,0,0,0,0,1,0)
                if any(abs(rest[i]-ideal[i])>1e-5 for i in range(12)) or abs(rest[15]-1)>1e-5:
                    raise ValueError("unsupported non-translation inverse bind")
                pose = worlds[js[jid]]
                x += weight*(v[0]+rest[12]+pose[0])
                y += weight*(v[1]+rest[13]+pose[1])
                z += weight*(v[2]+rest[14]+pose[2])
            if not finite_vec((x,y,z)):
                raise ValueError("nonfinite animated geometry")
            deformed.append((x,y,z))
        if k==0: first=deformed
        if k==count-1: last=deformed
        image=Image.new("RGB",(640,360),(13,22,38))
        draw=ImageDraw.Draw(image)
        def screen(p): return (round(320+p[0]*160),round(180-p[1]*160))
        for i in range(0,len(indices),3):
            tri=[indices[i+t][0] for t in range(3)]
            if max(tri)>=len(deformed):
                raise ValueError("triangle references absent vertex")
            draw.polygon([screen(deformed[t]) for t in tri],fill=(39,164,208),outline=(100,220,247))
        draw.rectangle((0,0,640,37),fill=(7,12,25))
        draw.text((12,12),"NASA R3 | independent GLB skin evaluator | 2D proxy",fill=(235,245,250))
        stamp=manifest["glb_frame_start_source_ms"]//1000+k
        draw.text((12,331),f"Source second {stamp} / Z=0 / no real body depth or likeness",fill=(195,210,225))
        image.save(out/f"rig_frame_{k:03d}.png")
    displacement=max(math.dist(a,b) for a,b in zip(first,last))
    if displacement < .002:
        raise ValueError("GLB skin animation failed deformation test")
    receipt={
      "status":"PASS_INDEPENDENT_GLTF_SUBSET_SKIN_NOT_BLENDER",
      "source_input_sha256":manifest["input_landmarks_sha256"],
      "input_glb_sha256":hashlib.sha256((out.parent/"camera_plane_skinned_motion.glb").read_bytes()).hexdigest(),
      "skinned_vertices":len(pos),"triangle_count":len(indices)//3,
      "skin_joints":len(js),"animation_channels":len(translations),
      "raster_frames":count,"displacement_camera_plane_units":displacement,
      "limits":"camera-plane, z=0, source missingness excludes gaps; no depth, anatomy, true rigging, physical contact, or independent identity",
      "reader":"Python stdlib glTF2 accessor/skin/animation parser; Pillow raster; Blender NOT_RUN"}
    if receipt["input_glb_sha256"]!=manifest["glb_sha256"]:
        raise ValueError("GLB manifest hash mismatch")
    (out/"portable_glb_validation.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt,indent=2))
    return receipt

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--glb",required=True)
    ap.add_argument("--manifest",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    raw=Path(a.glb).read_bytes()
    manifest=json.loads(Path(a.manifest).read_text())
    out=Path(a.out)
    out.mkdir(parents=True,exist_ok=True)
    doc,data=read_glb(raw)
    evaluate(doc,data,manifest,out)

if __name__=="__main__":main()
