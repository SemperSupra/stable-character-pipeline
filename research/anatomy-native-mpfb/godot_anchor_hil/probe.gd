extends SceneTree
## R047 explicit runtime controller for original-synthetic organ proxy morphs.
## Tests control-plane shape synchronization, NOT real organ registration.

func reject(message: String) -> void:
    push_error("R047_GODOT_ANCHOR_HOLD " + message)
    quit(12)

func get_names(mesh: MeshInstance3D) -> PackedStringArray:
    var result: PackedStringArray = []
    for i in range(mesh.mesh.get_blend_shape_count()):
        result.append(String(mesh.mesh.get_blend_shape_name(i)))
    return result

func _initialize() -> void:
    var packed: PackedScene = load("res://anchored.glb")
    if packed == null:
        reject("anchored original synthetic fixture not imported")
        return
    var scene: Node = packed.instantiate()
    get_root().add_child(scene)
    var bones: Array[Node] = scene.find_children("*", "Skeleton3D", true, false)
    var candidates: Array[Node] = scene.find_children("*", "MeshInstance3D", true, false)
    if bones.size() != 1 or (bones[0] as Skeleton3D).get_bone_count() != 163:
        reject("original official skeleton disappeared")
        return
    var body: MeshInstance3D = null
    var left: MeshInstance3D = null
    var right: MeshInstance3D = null
    for candidate: Node in candidates:
        var m: MeshInstance3D = candidate as MeshInstance3D
        if m.mesh == null:
            reject("empty imported mesh resource")
            return
        var name: String = String(m.name)
        if name.contains("R043_EditableMask_MPFB_Body"):
            body = m
        elif name.contains("R045_AnchorSynthetic_Left"):
            left = m
        elif name.contains("R045_AnchorSynthetic_Right"):
            right = m
    if body == null or left == null or right == null:
        reject("body or independently morphed synthetic organ missing")
        return
    var meshes: Array[MeshInstance3D] = [body,left,right]
    var channels: PackedStringArray = get_names(body)
    if channels.size() != 8:
        reject("expected eight source MPFB named relative shape morphs")
        return
    for m in meshes:
        if get_names(m) != channels:
            reject("inconsistent imported morph channel names on " + String(m.name))
            return
        if m.mesh.get_surface_count() != 1:
            reject("invalid mesh surface count on " + String(m.name))
            return
        if m.skin == null:
            reject("imported mesh has no skin binding on " + String(m.name))
            return
    if (body.mesh.surface_get_format(0) & Mesh.ARRAY_FLAG_USE_8_BONE_WEIGHTS) == 0:
        reject("body eight joint influence flag lost in anchored GLB")
        return
    var idx: int = 0
    var base_body: float = body.get_blend_shape_value(idx)
    var base_left: float = left.get_blend_shape_value(idx)
    var base_right: float = right.get_blend_shape_value(idx)
    if absf(base_body-base_left) > 0.0001 or absf(base_body-base_right) > 0.0001:
        reject("imported baseline body/organ morph values are not aligned")
        return
    # Negative control: changing only the body MUST NOT silently change other
    # mesh instances. The controller then explicitly broadcasts values.
    var test_value: float = 0.37
    body.set_blend_shape_value(idx,test_value)
    if absf(left.get_blend_shape_value(idx)-base_left) > 0.000001 or absf(right.get_blend_shape_value(idx)-base_right) > 0.000001:
        reject("unexpected hidden coupling between separate mesh morph values")
        return
    var control_updates: int = 0
    for m in meshes:
        for channel_idx in range(channels.size()):
            var new_value: float = 0.37 if channel_idx == idx else 0.19
            m.set_blend_shape_value(channel_idx,new_value)
            if absf(m.get_blend_shape_value(channel_idx)-new_value) > 0.00001:
                reject("morph controller write/read failed on " + String(m.name))
                return
            control_updates += 1
    print("R047_GODOT_ANCHOR_RECEIPT ", JSON.stringify({
        "schema": "r047.godot.synthetic-anchor-morph-control.v1",
        "status": "PASS_NARROW_THREE_MESH_RUNTIME_MORPH_SYNCHRONIZATION",
        "engine": Engine.get_version_info().get("string","UNKNOWN"),
        "skeleton_bones": (bones[0] as Skeleton3D).get_bone_count(),
        "source_morph_channel_names": channels,
        "morph_channels_per_mesh": channels.size(),
        "body_and_synthetic_organs": meshes.size(),
        "independent_value_negative_control": true,
        "explicit_controller_updates_checked": control_updates,
        "eight_weight_body_format": true,
        "limits": "NO_RENDERED_MORPH_SPATIAL_OR_REAL_ANATOMICAL_OR_PHYSICS_OR_GAMEPLAY_ACCEPTANCE"
    }))
    scene.queue_free()
    quit(0)
