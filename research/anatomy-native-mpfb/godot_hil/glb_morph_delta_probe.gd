extends SceneTree
## R050 eight-channel original synthetic MPFB GLB -> actual Godot Mesa
## GPU morph-delta binary. Independent numeric verifier reads glTF bytes.

func hold(message: String) -> void:
    push_error("R050_MORPH_DELTA_HOLD " + message)
    quit(12)

func vertices(mesh: ArrayMesh) -> PackedVector3Array:
    if mesh == null or mesh.get_surface_count() != 1:
        return PackedVector3Array()
    var arrays: Array = mesh.surface_get_arrays(0)
    return arrays[Mesh.ARRAY_VERTEX]

func _initialize() -> void:
    var packed: PackedScene = load("res://fixture.glb")
    if packed == null:
        hold("cannot load original pinned MPFB glTF fixture")
        return
    var scene: Node = packed.instantiate()
    get_root().add_child(scene)
    await process_frame
    await process_frame
    var body: MeshInstance3D = null
    for candidate: Node in scene.find_children("*", "MeshInstance3D",true,false):
        var mesh: MeshInstance3D = candidate as MeshInstance3D
        if mesh.mesh != null and mesh.mesh.get_blend_shape_count() == 8:
            if body != null:
                hold("multiple imported bodies have eight morph channels")
                return
            body = mesh
    if body == null:
        hold("no eight-morph body imported from pinned original GLB")
        return
    var base_values: Array[float] = []
    for i in range(8):
        base_values.append(body.get_blend_shape_value(i))
    var baseline: PackedVector3Array = vertices(body.bake_mesh_from_current_blend_shape_mix())
    if baseline.size() < 13000:
        hold("Mesa actual baseline baked morph vertex array absent")
        return
    var outfile: FileAccess = FileAccess.open("res://r050-godot-morph-delta.bin", FileAccess.WRITE)
    if outfile == null:
        hold("could not write isolated numeric source-safe array")
        return
    outfile.store_32(8)
    outfile.store_32(baseline.size())
    # Record actual engine baseline local-space coordinates for independent
    # source POSITION vertex correspondence and axis-frame calibration.
    for p: Vector3 in baseline:
        outfile.store_float(p.x)
        outfile.store_float(p.y)
        outfile.store_float(p.z)
    var max_movement: float = 0.0
    var nonzero_channels: int = 0
    for channel_idx in range(8):
        var target: float = 0.24
        body.set_blend_shape_value(channel_idx,base_values[channel_idx] + target)
        var changed: PackedVector3Array = vertices(body.bake_mesh_from_current_blend_shape_mix())
        if changed.size()!=baseline.size():
            hold("changing morph changed mesh vertex cardinality")
            return
        var channel_max: float = 0.0
        for i in range(baseline.size()):
            var d: Vector3 = changed[i]-baseline[i]
            if not is_finite(d.x) or not is_finite(d.y) or not is_finite(d.z):
                hold("nonfinite Godot baked morph source delta")
                return
            outfile.store_float(d.x)
            outfile.store_float(d.y)
            outfile.store_float(d.z)
            channel_max=maxf(channel_max,d.length())
        body.set_blend_shape_value(channel_idx,base_values[channel_idx])
        if channel_max > 0.00001:
            nonzero_channels+=1
        max_movement=maxf(max_movement,channel_max)
    outfile.flush()
    outfile.close()
    if nonzero_channels < 5:
        hold("few real source MPFB channels changed mesh coordinates")
        return
    print("R050_GODOT_MORPH_DELTA ",JSON.stringify({
        "schema":"r050.godot.gltf-source-morph-delta.v1",
        "status":"RECORDED_ACTUAL_GODOT_MESA_DELTAS_REQUIRES_INDEPENDENT_COMPARATOR",
        "godot_version":Engine.get_version_info().get("string","UNKNOWN"),
        "measured_eight_channels":8,
        "baked_vertices":baseline.size(),
        "nonzero_morphs":nonzero_channels,
        "max_individual_delta_m":max_movement,
        "stimulus_per_channel":0.24,
        "source":"exact original synthetic official MPFB glTF from inherited R044",
        "limits":"No comparison yet, no engine rest coordinate parity or actual real organ anatomy"
    }))
    scene.queue_free()
    quit(0)
