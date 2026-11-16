extends SceneTree
## R046 independent runtime Godot v4.5.2 shape-control, 8-influence
## surface-buffer and skeletal pose test on original synthetic public GLB.

func reject(message: String) -> void:
    push_error("R046_GODOT_RUNTIME_HOLD " + message)
    quit(12)

func _initialize() -> void:
    var packed: PackedScene = load("res://fixture.glb")
    if packed == null:
        reject("cannot load original source-safe GLB fixture")
        return
    var instance: Node = packed.instantiate()
    get_root().add_child(instance)
    var skeletons: Array[Node] = instance.find_children("*", "Skeleton3D", true, false)
    var meshes: Array[Node] = instance.find_children("*", "MeshInstance3D", true, false)
    var players: Array[Node] = instance.find_children("*", "AnimationPlayer", true, false)
    if skeletons.size() != 1 or players.is_empty():
        reject("actual skeleton/animation player absent")
        return
    var rig: Skeleton3D = skeletons[0] as Skeleton3D
    if rig.get_bone_count() != 163:
        reject("bone count changed")
        return
    var body: MeshInstance3D = null
    for candidate: Node in meshes:
        var m: MeshInstance3D = candidate as MeshInstance3D
        if m.mesh != null and m.mesh.get_blend_shape_count() >= 8:
            if body != null:
                reject("multiple body meshes with eight morphs")
                return
            body = m
    if body == null:
        reject("no actual editable morph surface")
        return
    if body.mesh.get_surface_count() != 1:
        reject("unexpected body topology/material surface count")
        return
    var format: int = body.mesh.surface_get_format(0)
    var uses_eight: bool = (format & Mesh.ARRAY_FLAG_USE_8_BONE_WEIGHTS) != 0
    if not uses_eight:
        reject("Godot imported glTF all-influences as four-bone vertex data; fidelity HOLD")
        return
    var arrays: Array = body.mesh.surface_get_arrays(0)
    var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
    var weights: PackedFloat32Array = arrays[Mesh.ARRAY_WEIGHTS]
    var bones: PackedInt32Array = arrays[Mesh.ARRAY_BONES]
    if points.size() < 13380 or weights.size() != points.size() * 8 or bones.size() != points.size() * 8:
        reject("Godot 8-bone geometry buffer/vertex ratio invalid")
        return
    var more_than_four: int = 0
    var max_nonzero: int = 0
    var max_sum_error: float = 0.0
    for i in range(points.size()):
        var count: int = 0
        var weight_sum: float = 0.0
        for k in range(8):
            var w: float = weights[i * 8 + k]
            if w < -0.0000001 or not is_finite(w):
                reject("nonfinite or negative Godot skin weight")
                return
            if w > 0.0000001:
                count += 1
            weight_sum += w
        max_nonzero = maxi(max_nonzero,count)
        if count > 4:
            more_than_four += 1
        if weight_sum > 0.0000001:
            max_sum_error = maxf(max_sum_error,absf(weight_sum - 1.0))
    if more_than_four < 100 or max_nonzero <= 4:
        reject("Godot imported eight slots but discarded >4 bone influences")
        return
    if max_sum_error > 0.001:
        reject("Godot skin weights have unnormalized sums: " + str(max_sum_error))
        return
    var shape_initial: float = body.get_blend_shape_value(0)
    body.set_blend_shape_value(0, 0.42)
    if absf(body.get_blend_shape_value(0) - 0.42) > 0.00001:
        reject("Godot morph control is not settable/readable")
        return
    body.set_blend_shape_value(0, shape_initial)

    var player: AnimationPlayer = players[0] as AnimationPlayer
    var animation_names: PackedStringArray = player.get_animation_list()
    var chosen: StringName = &""
    for item: StringName in animation_names:
        if String(item) != "RESET":
            chosen = item
            break
    if String(chosen).is_empty():
        reject("only RESET animation was imported")
        return
    var before_pos: Array[Vector3] = []
    var before_rot: Array[Quaternion] = []
    for i in range(rig.get_bone_count()):
        before_pos.append(rig.get_bone_pose_position(i))
        before_rot.append(rig.get_bone_pose_rotation(i))
    player.play(chosen)
    player.advance(0.5)
    var animated_bones: int = 0
    var max_bone_delta: float = 0.0
    for i in range(rig.get_bone_count()):
        var dp: float = rig.get_bone_pose_position(i).distance_to(before_pos[i])
        var dr: float = rig.get_bone_pose_rotation(i).angle_to(before_rot[i])
        if dp + dr > 0.000001:
            animated_bones += 1
        max_bone_delta = maxf(max_bone_delta, dp + dr)
    if animated_bones == 0:
        reject("Godot animation advanced but imported skeletal pose did not change")
        return
    print("R046_GODOT_RUNTIME_RECEIPT ", JSON.stringify({
        "schema": "r046.godot.8-bone-animation.v1",
        "status": "PASS_NARROW_GODOT_8_INFLUENCE_BUFFER_AND_POSE",
        "godot_version": Engine.get_version_info().get("string","UNKNOWN"),
        "body_vertices": points.size(),
        "8_influences_flag": uses_eight,
        "vertices_with_more_than_four_nonzero_influences": more_than_four,
        "maximum_nonzero_weights_per_vertex": max_nonzero,
        "maximum_weight_sum_error": max_sum_error,
        "morph_slider_readwrite": true,
        "animation_clip": String(chosen),
        "animated_bone_count": animated_bones,
        "maximum_pose_change": max_bone_delta,
        "limits": "NO_RENDERED_VERTEX_GEOMETRY_OR_BIOLOGICAL_FIDELITY_OR_RELEASE_ACCEPTANCE"
    }))
    instance.queue_free()
    quit(0)
