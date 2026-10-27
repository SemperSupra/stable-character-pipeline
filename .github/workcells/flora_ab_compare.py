#!/usr/bin/env python3
"""F1e: reproducible, same-camera comparison of three synthetic vegetation sources.

A = existing original Go banana proxy; B = MTG/L-Py/PlantGL fixture;
C = original Go palm proxy. NOT an accuracy ranking or botanical calibration.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


EXPECTED_BASELINE_SHA = "67b503b6903de319739ea35a456dea270739f6fde30938e6c555de6451da972a"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_children(obj):
    result = []
    todo = list(obj.children)
    while todo:
        obj = todo.pop()
        if obj.type == "MESH":
            result.append(obj)
        todo.extend(obj.children)
    return result


def bounds(meshes):
    pts = [obj.matrix_world @ vert.co for obj in meshes for vert in obj.data.vertices]
    if not pts:
        raise RuntimeError("empty input mesh collection")
    bb = [[min(v[i] for v in pts) for i in range(3)], [max(v[i] for v in pts) for i in range(3)]]
    if any(not math.isfinite(x) for row in bb for x in row):
        raise RuntimeError("non-finite geometry extent")
    return bb


def quantify(meshes):
    bb = bounds(meshes)
    ext = [bb[1][i]-bb[0][i] for i in range(3)]
    if min(ext) < .001 or max(ext) > 50:
        raise RuntimeError("degenerate or unbounded comparison geometry")
    return {"mesh_count": len(meshes),
            "vertex_count": sum(len(o.data.vertices) for o in meshes),
            "triangle_count": sum(sum(len(poly.vertices)-2 for poly in o.data.polygons) for o in meshes),
            "bounds_m": [[round(v, 6) for v in side] for side in bb],
            "extent_m": [round(v, 6) for v in ext],
            "height_m": round(ext[2], 6),
            "width_height_ratio": round(max(ext[0],ext[1])/ext[2], 6)}


def parse_baseline_glb(path):
    # JSON chunk inspection avoids silently selecting a surrogate asset.
    import struct
    data = path.read_bytes()
    if data[:4] != b"glTF" or struct.unpack_from("<I",data,8)[0] != len(data):
        raise RuntimeError("malformed original Go GLB")
    n, typ = struct.unpack_from("<II",data,12)
    if typ != 0x4e4f534a:
        raise RuntimeError("missing GLB JSON chunk")
    doc = json.loads(data[20:20+n])
    names = [o.get("name") for o in doc["nodes"]]
    for label, prefix, expected in [
            ("banana","flora/banana-00",9),
            ("palm","flora/palm-00",11)]:
        matches=[x for x in names if isinstance(x,str) and x.startswith(prefix+"/")]
        if len(matches) != expected or prefix+"/root" not in matches:
            raise RuntimeError("changed Go source plant identity contract: "+label)
    return {"nodes":len(doc["nodes"]), "meshes":len(doc["meshes"])}


def imported_roots(before, prefix, expected):
    # The Go glTF nodes are named and nested by source; do NOT select by color.
    roots = [o for o in before if o.name == prefix+"/root"]
    if len(roots) != 1:
        raise RuntimeError("Go import cannot identify exact source root: "+prefix+
                           "; candidates: "+repr([o.name for o in before if prefix.split("/")[-1] in o.name][:20]))
    meshes = source_children(roots[0])
    if len(meshes) != expected:
        raise RuntimeError("Go source subgraph changed: "+prefix+" "+str(len(meshes)))
    return meshes


def main():
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    p=argparse.ArgumentParser()
    p.add_argument("--original-glb",required=True)
    p.add_argument("--derived-glb",required=True)
    p.add_argument("--roundtrip-receipt",required=True)
    p.add_argument("--scene-config",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args(argv)
    out=Path(args.out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    go_path=Path(args.original_glb).resolve()
    f1_path=Path(args.derived_glb).resolve()
    f1_receipt=json.loads(Path(args.roundtrip_receipt).read_text())
    config=json.loads(Path(args.scene_config).read_text())
    if config.get("schema")!="tropical.scene.v0" or config.get("seed") != 1337:
        raise RuntimeError("unexpected Go baseline config")
    actual_go_sha=digest(go_path)
    if actual_go_sha != EXPECTED_BASELINE_SHA:
        raise RuntimeError("Go baseline SHA drift: "+actual_go_sha)
    if f1_receipt.get("schema")!="scp.flora.glb_roundtrip.v1" or digest(f1_path)!=f1_receipt["glb_sha256"]:
        raise RuntimeError("unproven specialist input geometry")
    source_glb=parse_baseline_glb(go_path)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(go_path))
    go_objs=list(bpy.data.objects)
    banana=imported_roots(go_objs,"flora/banana-00",8)
    palm=imported_roots(go_objs,"flora/palm-00",10)
    prior=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(f1_path))
    derived=[o for o in bpy.data.objects if o not in prior and o.type == "MESH" and o.get("scp_organ_id")]
    if len(derived)!=15 or len({o["scp_organ_id"] for o in derived})!=15:
        raise RuntimeError("F1c import missing unique MTG-derived organs")
    groups={"go_banana": banana,"openalea_fixture":derived,"go_palm":palm}
    metrics={label:quantify(objects) for label,objects in groups.items()}
    if metrics["go_banana"]["mesh_count"]!=8 or metrics["go_palm"]["mesh_count"]!=10:
        raise RuntimeError("source leaf/frond count changed")
    scene=bpy.context.scene
    scene.render.engine="BLENDER_WORKBENCH"
    scene.display.shading.color_type="OBJECT"
    scene.render.resolution_x=640
    scene.render.resolution_y=480
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    for obj in banana+palm+derived:
        obj.color=(.18,.45,.16,1) if any(k in obj.name.lower() for k in ("leaf","frond")) or obj.get("scp_kind")=="leaf" else (.44,.29,.17,1)
    cam_data=bpy.data.cameras.new("ab_orthographic_camera")
    cam_data.type="ORTHO"
    cam=bpy.data.objects.new("ab_orthographic_camera",cam_data)
    scene.collection.objects.link(cam)
    scene.camera=cam
    # Identical metric framing for all three sources: no per-model rescale.
    fixed_span=max(max(m["extent_m"]) for m in metrics.values())
    cam_data.ortho_scale=fixed_span*2.1
    views={}
    for label,meshes in groups.items():
        visible=set(meshes)
        # Turn off every original scene object except the selected real meshes.
        for obj in bpy.data.objects:
            if obj.type=="MESH":
                obj.hide_render=(obj not in visible)
        bb=metrics[label]["bounds_m"]
        center=Vector(tuple((bb[0][i]+bb[1][i])*.5 for i in range(3)))
        direction=Vector((3,-5,2.5)).normalized()
        cam.location=center+direction*fixed_span*4
        cam.rotation_euler=(center-cam.location).to_track_quat("-Z","Y").to_euler()
        target=out/("ab_"+label+".png")
        scene.render.filepath=str(target)
        bpy.ops.render.render(write_still=True)
        if not target.exists() or target.stat().st_size < 4096 or target.read_bytes()[:8]!=b"\x89PNG\r\n\x1a\n":
            raise RuntimeError("missing native Blender A/B frame "+label)
        views[label]=digest(target)
    if len(set(views.values()))!=3:
        raise RuntimeError("duplicate A/B source frames")
    evidence={
        "schema":"scp.flora.ab-comparison.v1",
        "fidelity":"SYNTHETIC_TECHNICAL_PROXY_NOT_BOTANICAL_ACCURACY",
        "comparison":"Go banana vs real upstream L-Py/MTG/PlantGL synthetic fixture vs Go palm; no same-species ground truth",
        "methods":"native imported GLB meshes, full world bounds, Z-up meters only for Go; F1 unit illustrative; identical fixed ortho scale and camera direction, independently recentered; no mesh rescaling",
        "go_source_glb_sha256":actual_go_sha,
        "go_scene_config_sha256":digest(Path(args.scene_config)),
        "go_source_inventory":source_glb,
        "specialist_source_glb_sha256":digest(f1_path),
        "specialist_roundtrip_receipt_sha256":digest(Path(args.roundtrip_receipt)),
        "blender_version":bpy.app.version_string,
        "camera_ortho_scale":round(cam_data.ortho_scale,6),
        "metrics":metrics, "views_sha256":views,
        "limitations":["different proxy types and assumed F1 units; dimensions are not biologically commensurate",
                       "no botanical references or species homologous ground truth",
                       "no leaf attachment, wind, development, physics or light validation"]
    }
    evidence["digest_sha256"]=hashlib.sha256(json.dumps(evidence,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    (out/"ab_receipt.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
    print("FLORA_AB_COMPARISON_PASS "+json.dumps({
        "source_sha256":actual_go_sha,"view_hashes":views,"metric_heights":{k:v["height_m"] for k,v in metrics.items()},
        "digest_sha256":evidence["digest_sha256"]},sort_keys=True))


if __name__=="__main__":
    main()
