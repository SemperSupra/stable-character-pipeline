# Independent synthetic native Blender re-open check; no private inputs.
import bpy
import json
import pathlib
import sys

def main(folder):
    path = pathlib.Path(folder) / "synthetic-csg.blend"
    assert path.is_file(), "Native Blender file was not created"
    bpy.ops.wm.open_mainfile(filepath=str(path))
    root = bpy.data.objects.get("tiny_disconnected_union")
    assert root is not None, "Native root object identity disappeared"
    mods = [m for m in root.modifiers if m.type == "BOOLEAN"]
    assert len(mods) >= 1 and all(m.object is not None for m in mods), "Native Boolean editability lost"
    assert all(m.solver == 'EXACT' for m in mods), "Native Boolean solver not retained"
    assert bpy.context.scene.unit_settings.system == 'NONE' or bpy.context.scene.unit_settings.scale_length == 1.0
    receipt = {
        "fixture": "r97-public-blend-reopen",
        "blender_version": bpy.app.version_string,
        "native_root": root.name,
        "boolean_modifiers": len(mods),
        "status": "NATIVE_EDITABLE_MODIFIERS_PRESENT",
    }
    print("R97 NATIVE BLEND REOPEN PASS", json.dumps(receipt, sort_keys=True))

if __name__ == "__main__":
    if "--" not in sys.argv:
        raise SystemExit("Expected -- OUTDIR")
    values = sys.argv[sys.argv.index("--") + 1:]
    assert len(values) == 1
    main(values[0])
