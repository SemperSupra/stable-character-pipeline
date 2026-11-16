extends SceneTree
## R048 independent Godot 4.5.2 rendered-mesh GPU readback of original
## source-safe MPFB GLB. Mesa llvmpipe/Xvfb, no private identities.

func hold(reason: String) -> void:
    push_error("R048_GODOT_BAKE_HOLD " + reason)
    quit(12)

func vertices(mesh: ArrayMesh) -> PackedVector3Array:
    if mesh == null or mesh.get_surface_count() < 1:
        return PackedVector3Array()
    var arrays: Array = mesh.surface_get_arrays(0)
    return arrays[Mesh.ARRAY_VERTEX]

func max_delta(a: PackedVector3Array,b: PackedVector3Array) -> float:
    if a.size() != b.size() or a.is_empty():
        return -1.0
    var largest: float = 0.0
    for i in range(a.size()):
        var distance: float = a[i].distance_to(b[i])
        if not is_finite(distance):
            return -1.0
        largest = maxf(largest,distance)
    return largest

func _initialize() -> void:
    var packed: PackedScene = load("res://fixture.glb")
    if packed == null:
        hold("original synthetic GLB not imported")
        return
    var scene: Node = packed.instantiate()
    get_root().add_child(scene)
    # Allow Skeleton3D skin registration and real renderer mesh instances
    # to finish binding before GPU readback; still fail if no valid skin.
    await process_frame
    await process_frame
    var body: MeshInstance3D = null
    for candidate: Node in scene.find_children("*","MeshInstance3D",true,false):
        var m: MeshInstance3D = candidate as MeshInstance3D
        if m.mesh != null and m.mesh.get_blend_shape_count() == 8:
            body = m
            break
    var players: Array[Node] = scene.find_children("*","AnimationPlayer",true,false)
    if body == null or players.is_empty():
        hold("independent imported source body morphs or skeleton animation absent")
        return
    var base: PackedVector3Array = vertices(body.bake_mesh_from_current_blend_shape_mix())
    if base.size() < 13000:
        hold("baked baseline actual GPU morph surface missing: "+str(base.size()))
        return
    var original: float = body.get_blend_shape_value(0)
    var change: float = minf(0.9,original+0.24)
    if absf(change-original)<0.05:
        hold("unable to perturb original morph control")
        return
    body.set_blend_shape_value(0,change)
    var changed: PackedVector3Array = vertices(body.bake_mesh_from_current_blend_shape_mix())
    var morph_delta: float = max_delta(base,changed)
    if morph_delta <= 0.00001:
        hold("live GPU baked external body morph did not respond: "+str(morph_delta))
        return
    body.set_blend_shape_value(0,original)
    var restored: PackedVector3Array = vertices(body.bake_mesh_from_current_blend_shape_mix())
    var restore_delta: float = max_delta(base,restored)
    if restore_delta < 0 or restore_delta > 0.000005:
        hold("GPU baked morph failed reversible control: "+str(restore_delta))
        return

    print("R048_GODOT_SKIN_DEBUG ",JSON.stringify({
        "body_skin":body.skin != null,
        "skin_reference":body.get_skin_reference() != null,
        "skeleton_path":String(body.skeleton),
        "body_parent":body.get_parent().name
    }))
    if body.skin == null or body.get_skin_reference() == null:
        hold("actual renderer scene has no registered skin after two frames")
        return
    var base_skin: PackedVector3Array = vertices(body.bake_mesh_from_current_skeleton_pose())
    if base_skin.size() != base.size():
        hold("GPU bake skeleton/base morph vertex cardinality differs")
        return
    var player: AnimationPlayer = players[0] as AnimationPlayer
    var clip: StringName = &""
    for name: StringName in player.get_animation_list():
        if String(name) != "RESET":
            clip=name
            break
    if String(clip).is_empty():
        hold("imported skeletal motion clip missing")
        return
    player.play(clip)
    player.advance(0.50)
    var skinned: PackedVector3Array = vertices(body.bake_mesh_from_current_skeleton_pose())
    var skin_delta: float = max_delta(base_skin,skinned)
    if skin_delta <= 0.00001:
        hold("live GPU skinned geometry unchanged with bone animation: "+str(skin_delta))
        return
    print("R048_GODOT_BAKE_RECEIPT ",JSON.stringify({
        "schema":"r048.godot.rendered-morph-skin.v1",
        "status":"PASS_NARROW_RENDERER_BAKED_BODY_MORPH_AND_SKELETAL_DEFORMATION",
        "engine":Engine.get_version_info().get("string","UNKNOWN"),
        "rendering_method":String(ProjectSettings.get_setting("rendering/renderer/rendering_method","unknown")),
        "baked_vertices":base.size(),
        "original_shape_value":original,
        "perturbed_shape_value":change,
        "max_baked_morph_delta_m":morph_delta,
        "max_baked_morph_restore_error_m":restore_delta,
        "max_baked_skeleton_motion_delta_m":skin_delta,
        "limits":"One original source-safe body morph and imported skeletal action; no native Blender position parity, anatomical organ registration, full physics/photoreal/game performance or product release"
    }))
    scene.queue_free()
    quit(0)
