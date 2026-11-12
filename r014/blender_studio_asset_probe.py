"""Independent official Blender Studio CC0 human-base sculpt mesh inventory.

This is a sculpt foundation/geometry inventory, not a rig, identity, internal
organ model, soft-body solver, facial performance or video realism acceptance.
"""
import argparse,hashlib,json,sys,tempfile,zipfile
from pathlib import Path
import bpy

p=argparse.ArgumentParser()
p.add_argument("--archive",type=Path,required=True)
p.add_argument("--out",type=Path,required=True)
p.add_argument("--receipt",type=Path,required=True)
args=p.parse_args(sys.argv[sys.argv.index("--")+1:])
args.out.mkdir(parents=True,exist_ok=True)

assert args.archive.stat().st_size==50643039,"official v1.4.1 archive byte count changed"
sha=hashlib.sha256()
with args.archive.open("rb") as src:
    while chunk:=src.read(1024*1024):sha.update(chunk)
with zipfile.ZipFile(args.archive) as z:
    assert z.testzip() is None,"ZIP CRC error"
    names=z.namelist()
    assert all(not n.startswith("/") and ".." not in n.split("/") for n in names)
    blend_paths=[n for n in names if n.lower().endswith(".blend")]
    assert blend_paths,"No native Blender file in official bundle"
    # Zip content can contain library documentation, text, and other resources.
    # Do not extract arbitrary ZIP members to persistent project directories.
    with tempfile.TemporaryDirectory(prefix="r014-official-") as tmp:
        path=Path(tmp)/"bundle.blend"
        with z.open(blend_paths[0]) as inp,path.open("wb") as dst:
            import shutil
            shutil.copyfileobj(inp,dst)
        with bpy.data.libraries.load(str(path),link=False) as (src,dst):
            all_object_names=list(src.objects)
            selections=[n for n in all_object_names if
                        "realistic" in n.lower() and
                        (("male" in n.lower() and "female" not in n.lower()) or
                         ("female" in n.lower()))]
            assert any("female" in n.lower() for n in selections),("female realistic base missing",selections)
            assert any("male" in n.lower() and "female" not in n.lower() for n in selections),("male realistic base missing",selections)
            dst.objects=selections
        objects=[o for o in dst.objects if o is not None]
        for obj in objects:
            bpy.context.collection.objects.link(obj)
        bodies=[o for o in objects if o.type=="MESH"]
        assert len(bodies)>=2,"realistic assets not renderable"
        inv=[]
        for obj in bodies:
            morph=obj.data.shape_keys
            inv.append({
                "name":obj.name,
                "vertices":len(obj.data.vertices),
                "faces":len(obj.data.polygons),
                "uv_sets":len(obj.data.uv_layers),
                "modifiers":[{"type":m.type,"name":m.name} for m in obj.modifiers],
                "morphs":len(morph.key_blocks) if morph else 0,
                "rigged":any(m.type=="ARMATURE" for m in obj.modifiers),
                "dimensions_blender":list(obj.dimensions),
                "material_slots":len(obj.material_slots)
            })
        assert all(x["vertices"]>=2000 for x in inv),inv
        # Preserve original sculpt modifiers; do not falsely substitute a
        # rasterized high-poly render for an editable native multires base.
        target=args.out/"R014_BlenderStudio_CC0_realistic_sculpt_bases.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(target))
        receipt={
            "status":"PASS_PUBLISHER_ARCHIVE_INVENTORY_ONLY",
            "source":"Blender Studio official Human Base Meshes v1.4.1",
            "publisher_url":"https://download.blender.org/demo/asset-bundles/human-base-meshes/human-base-meshes-bundle-v1.4.1.zip",
            "license_source":"Blender source repository developer asset bundle CC0",
            "claimed_bundle_license":"CC0",
            "sha256_first_observed":sha.hexdigest(),
            "source_zip_bytes":args.archive.stat().st_size,
            "blend_entries":blend_paths,
            "all_library_object_names":all_object_names,
            "selected_realistic_bases":inv,
            "native_research_blend":target.name,
            "promotion_state":"HOLD_UNTIL_PINNED_SHA_REPETITION_AND_VISUAL_ANATOMY_REVIEW",
            "limits":["Sculpt bases only; no demonstrated full rig, motion or cloth/tissue physics",
                      "No verified external genitalia; some Blender male references omit genitals",
                      "No CC BY data silently blended into CC0 base",
                      "No cinematic photoreal skin/hair/eyes/video pass",
                      "First download digest must be pinned and independently reverified"]
        }
        args.receipt.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
        print("R014_BLENDER_STUDIO_BASES",json.dumps({k:v for k,v in receipt.items()
                  if k not in ("all_library_object_names","selected_realistic_bases","limits")},sort_keys=True))
        print("R014_BLENDER_STUDIO_MESHES",json.dumps(inv,sort_keys=True))
