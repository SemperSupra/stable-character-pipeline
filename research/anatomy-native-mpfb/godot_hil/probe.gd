extends SceneTree
## R045 independent Godot v4.5.2 headless GLB import and morph/armature
## structural evaluation. Does not qualify runtime appearance or physiology.

func reject(message: String) -> void:
    push_error("R045_GODOT_GLTF_HOLD " + message)
    quit(12)

func _initialize() -> void:
    var scene: PackedScene = load("res://fixture.glb")
    if scene == null:
        reject("actual imported fixture.glb unavailable")
        return
    var root: Node = scene.instantiate()
    if root == null:
        reject("cannot instantiate actual glTF scene")
        return
    var skeletons: Array[Node] = root.find_children("*", "Skeleton3D", true, false)
    var meshes: Array[Node] = root.find_children("*", "MeshInstance3D", true, false)
    var players: Array[Node] = root.find_children("*", "AnimationPlayer", true, false)
    if skeletons.size() != 1:
        reject("expected exactly one source skeletal armature")
        root.free()
        return
    var bones: int = (skeletons[0] as Skeleton3D).get_bone_count()
    if bones != 163:
        reject("imported skeleton bone count changed: " + str(bones))
        root.free()
        return
    if meshes.size() < 3:
        reject("expected visible external body and two synthetic organ meshes")
        root.free()
        return
    var morph_meshes: int = 0
    var max_blend_shapes: int = 0
    var names: Array[String] = []
    var blend_names: Array[String] = []
    var mesh_surfaces: int = 0
    for candidate: Node in meshes:
        var mesh: MeshInstance3D = candidate as MeshInstance3D
        names.append(String(mesh.name))
        if mesh.mesh == null:
            reject("imported mesh has no actual surface resource")
            root.free()
            return
        mesh_surfaces += mesh.mesh.get_surface_count()
        if mesh.mesh.get_surface_count() <= 0:
            reject("empty mesh surface")
            root.free()
            return
        var shape_count: int = mesh.mesh.get_blend_shape_count()
        if shape_count > 0:
            morph_meshes += 1
            max_blend_shapes = maxi(max_blend_shapes, shape_count)
            for i in range(shape_count):
                blend_names.append(String(mesh.mesh.get_blend_shape_name(i)))
    if morph_meshes != 1 or max_blend_shapes < 8:
        reject("Godot did not reimport eight editable shape morph channels: " + str(max_blend_shapes))
        root.free()
        return
    var organ_count: int = 0
    for name in names:
        if name.contains("R036_AnatomyProxy_"):
            organ_count += 1
    if organ_count != 2:
        reject("Godot failed to identify two original synthetic organ proxy meshes: " + str(names))
        root.free()
        return
    if players.size() < 1:
        reject("actual imported animations unavailable")
        root.free()
        return
    print("R045_GODOT_IMPORTED_RECEIPT ", JSON.stringify({
        "schema": "r045.godot.glb.interop.v1",
        "status": "PASS_NARROW_INDEPENDENT_GODOT_INTERCHANGE",
        "engine_version": Engine.get_version_info().get("string","UNKNOWN"),
        "skeleton_bones": bones,
        "mesh_nodes": meshes.size(),
        "mesh_surfaces": mesh_surfaces,
        "morph_meshes": morph_meshes,
        "max_blend_shapes": max_blend_shapes,
        "blend_shape_names": blend_names,
        "synthetic_organ_proxies": organ_count,
        "animation_player_count": players.size(),
        "disposition": "NO_MORPH_SKIN_RUNTIME_RENDER_PHYSICS_OR_RELEASE_ACCEPTANCE"
    }))
    root.free()
    quit(0)
