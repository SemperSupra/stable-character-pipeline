import bpy, sys, json, hashlib, os, math
from pathlib import Path
mode = sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "build"
root = Path(os.environ.get("R092_DIR","/tmp/r092-blender"))
root.mkdir(parents=True,exist_ok=True)
scene_path = root/"synthetic.blend"
expected = os.environ.get("R092_VERSION","")
actual = ".".join(str(i) for i in bpy.app.version)
assert actual == expected, f"version mismatch: expected {expected} got {actual}"
def obj_digest(ob, frame):
    bpy.context.scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    mesh = ob.evaluated_get(dg).to_mesh()
    try:
        vals = ",".join("%.8f,%.8f,%.8f"%tuple(v.co) for v in mesh.vertices)
        return hashlib.sha256(vals.encode()).hexdigest()
    finally:
        ob.evaluated_get(dg).to_mesh_clear()
if mode == "build":
    bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.object;obj.name="SyntheticBody"
    obj.shape_key_add(name="Basis")
    key=obj.shape_key_add(name="Breath")
    for v in key.data:
        if v.co.z>0:
            v.co.x *= 1.04
    for f,val in ((1,0.0),(12,1.0),(24,0.0)):
        key.value=val;key.keyframe_insert(data_path="value",frame=f)
    # Explicit camera required by headless Blender render on every tested version.
    cam_data=bpy.data.cameras.new("WitnessCamera")
    cam=bpy.data.objects.new("WitnessCamera",cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location=(4.0,-6.0,3.0)
    direction=-cam.location
    cam.rotation_euler=direction.to_track_quat("-Z","Y").to_euler()
    bpy.context.scene.camera=cam
    bpy.context.scene.render.engine="BLENDER_WORKBENCH"
    bpy.context.scene.render.resolution_x=64
    bpy.context.scene.render.resolution_y=64
    bpy.context.scene.render.resolution_percentage=100
    bpy.context.scene.frame_end=24
    bpy.ops.wm.save_as_mainfile(filepath=str(scene_path))
    print(json.dumps({"phase":"build","version":actual,"file_saved":scene_path.is_file()}))
elif mode == "audit":
    bpy.ops.wm.open_mainfile(filepath=str(scene_path))
    obj=bpy.data.objects.get("SyntheticBody")
    assert obj is not None and obj.type=="MESH"
    d=[obj_digest(obj,f) for f in (1,12,24)]
    assert d[0]!=d[1], "shape did not deform"
    assert d[0]==d[2], "shape failed to reset"
    bpy.context.scene.render.filepath=str(root/"witness.png")
    bpy.ops.render.render(write_still=True)
    img=root/"witness.png"
    assert img.exists() and img.stat().st_size>100
    print("R092_RECEIPT "+json.dumps({"phase":"audit","version":actual,"result":"PASS_CORE_SYNTHETIC","frame_hashes":d,"render_sha256":hashlib.sha256(img.read_bytes()).hexdigest(),"scene_sha256":hashlib.sha256(scene_path.read_bytes()).hexdigest(),"mpfb":"HOLD","biomechanics":"HOLD","release":"HOLD"},sort_keys=True))
else:
    raise ValueError(mode)
