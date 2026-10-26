#!/usr/bin/env python3
"""F1c: Blender imports true PlantGL-derived OBJ, exports GLB, reimports and checks."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds(obj):
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    return [[float(min(p[i] for p in points)) for i in range(3)],
            [float(max(p[i] for p in points)) for i in range(3)]]


def same_bounds(a, b, tol=0.0005):
    return all(abs(a[j][i] - b[j][i]) <= tol for j in range(2) for i in range(3))


def main():
    cli = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(cli)
    source, out = Path(args.source).resolve(), Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((source/"source_receipt.json").read_text())
    if manifest.get("schema") != "scp.flora.mtg_interchange.v1":
        raise RuntimeError("unexpected source schema")
    organs = manifest["organ_records"]
    if len(organs) != 15 or len(set(o["organ_id"] for o in organs)) != 15:
        raise RuntimeError("non-unique or missing MTG organ lineage")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    prior = {}
    for organ in organs:
        path = (source/organ["obj"]).resolve()
        if path.parent != source or digest(path) != organ["obj_sha256"]:
            raise RuntimeError("source OBJ rights/custody/path mismatch")
        before = set(bpy.data.objects)
        bpy.ops.wm.obj_import(filepath=str(path), forward_axis="Y", up_axis="Z")
        imported = [obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"]
        if len(imported) != 1:
            raise RuntimeError(f"expected exactly one imported mesh for {organ['organ_id']}, got {len(imported)}")
        obj = imported[0]
        obj.name = organ["organ_id"]
        obj["scp_organ_id"] = organ["organ_id"]
        obj["scp_mtg_vid"] = organ["mtg_vid"]
        obj["scp_parent_vid"] = organ["parent_vid"] if organ["parent_vid"] is not None else -1
        obj["scp_kind"] = organ["kind"]
        obj["scp_source_sha256"] = organ["obj_sha256"]
        if len(obj.data.vertices) < 3 or len(obj.data.polygons) < 1:
            raise RuntimeError("empty imported OBJ mesh")
        b = bounds(obj)
        if not same_bounds(b, organ["source_bounds_m"]):
            raise RuntimeError(f"PlantGL->OBJ->Blender axis/units mismatch {organ['organ_id']}: {b} / {organ['source_bounds_m']}")
        prior[organ["organ_id"]] = {"bounds": b, "vertices":len(obj.data.vertices),
                                     "triangles":sum(len(f.vertices)-2 for f in obj.data.polygons)}
    glb = out/"synthetic_flora_lineage.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", export_extras=True)
    if not glb.is_file() or glb.stat().st_size < 2048:
        raise RuntimeError("GLB export failed")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    restored = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    if len(restored) != 15 or len(set(obj.get("scp_organ_id") for obj in restored)) != 15:
        raise RuntimeError("GLB reimport dropped or duplicated organ IDs")
    by_id = {organ["organ_id"]: organ for organ in organs}
    for obj in restored:
        ident = obj.get("scp_organ_id")
        if ident not in prior:
            raise RuntimeError("unrecognized reimported organ")
        expected = by_id[ident]
        if (obj.get("scp_mtg_vid") != expected["mtg_vid"] or
            obj.get("scp_parent_vid") != (expected["parent_vid"] if expected["parent_vid"] is not None else -1) or
            obj.get("scp_source_sha256") != expected["obj_sha256"]):
            raise RuntimeError("GLB lineage/rights metadata not preserved: "+ident)
        if not same_bounds(bounds(obj), prior[ident]["bounds"]):
            raise RuntimeError("GLB reimport changed geometric bounds: "+ident)
    # Workbench-only visual diagnostics; these are not species-accurate materials.
    from mathutils import Vector
    scene = bpy.context.scene
    all_v = [ob.matrix_world @ v.co for ob in restored for v in ob.data.vertices]
    low = Vector(tuple(min(v[i] for v in all_v) for i in range(3)))
    high = Vector(tuple(max(v[i] for v in all_v) for i in range(3)))
    center = (low + high) * .5
    span = max(high[i]-low[i] for i in range(3))
    if not .1 < span < 50:
        raise RuntimeError("unbounded geometry in visual gate")
    for ob in restored:
        ob.color = (.20,.55,.20,1) if ob.get("scp_kind") == "leaf" else (.60,.33,.16,1)
    camera_data = bpy.data.cameras.new("diagnostic")
    camera_data.type, camera_data.ortho_scale = "ORTHO", span*2.0
    camera = bpy.data.objects.new("diagnostic",camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.color_type = "OBJECT"
    scene.render.resolution_x, scene.render.resolution_y = 640,480
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    views = {}
    for name,direction in (("front",(3,-5,2)),("side",(-5,-2,3))):
        camera.location = center + Vector(direction).normalized()*span*3.5
        camera.rotation_euler = (center-camera.location).to_track_quat("-Z","Y").to_euler()
        target = out/("diagnostic_"+name+".png")
        scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        if target.stat().st_size < 4096 or target.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError("invalid diagnostic PNG "+name)
        views[name] = digest(target)
    if views["front"] == views["side"]:
        raise RuntimeError("identical different-camera diagnostic images")
    bpy.ops.wm.save_as_mainfile(filepath=str(out/"synthetic_flora_lineage.blend"))
    receipt = {
        "schema": "scp.flora.glb_roundtrip.v1",
        "source_receipt_sha256": digest(source/"source_receipt.json"),
        "source_organs": len(organs), "glb_organs": len(restored),
        "glb_sha256": digest(glb), "blender_version": bpy.app.version_string,
        "organ_geometry": prior,
        "fidelity": "SYNTHETIC_INTERCHANGE_ONLY",
        "diagnostic_views": views,
        "status": "OBJ_GEOMETRY_AND_GLB_LINEAGE_BOUNDS_PASS"
    }
    (out/"roundtrip_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
    print("F1C_BLENDER_GLB_ROUNDTRIP_PASS "+json.dumps({
        "organs":len(restored),"glb_sha256":receipt["glb_sha256"]},sort_keys=True))


if __name__ == "__main__":
    main()
