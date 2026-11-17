extends SceneTree
## Independent real Godot 4.5.2 import and evaluated bone animation.
## Original self-authored 1-bone GLB only; no human or source media.

func reject(code: String) -> void:
    push_error("R3_GODOT_ANIMATION_HOLD " + code)
    quit(12)

func _initialize() -> void:
    var args: PackedStringArray = OS.get_cmdline_user_args()
    if args.size() != 2 or args[0] != "--lane" or not (args[1] in ["linear", "nonlinear"]):
        reject("UNKNOWN_EXPERIMENT_LANE")
        return
    var lane: String = args[1]
    var loaded: PackedScene = load("res://fixture.glb")
    if loaded == null:
        reject("ACTUAL_GLTF_IMPORT_MISSING")
        return
    var scene: Node = loaded.instantiate()
    if scene == null:
        reject("GLTF_INSTANTIATION_FAILED")
        return
    root.add_child(scene)
    var skeletons: Array[Node] = scene.find_children("*", "Skeleton3D", true, false)
    var meshes: Array[Node] = scene.find_children("*", "MeshInstance3D", true, false)
    var players: Array[Node] = scene.find_children("*", "AnimationPlayer", true, false)
    if skeletons.size() != 1 or meshes.size() != 1 or players.size() < 1:
        reject("NO_UNIQUE_SKELETON_MESH_PLAYER " + str([skeletons.size(),meshes.size(),players.size()]))
        return
    var skeleton: Skeleton3D = skeletons[0] as Skeleton3D
    var mesh: MeshInstance3D = meshes[0] as MeshInstance3D
    var player: AnimationPlayer = players[0] as AnimationPlayer
    if skeleton.get_bone_count() != 1 or mesh.mesh == null or mesh.mesh.get_surface_count() < 1:
        reject("SOURCE_RIG_OR_MESH_STRUCTURE_MISMATCH")
        return
    if mesh.skin == null:
        reject("ACTUAL_SKIN_BINDING_MISSING")
        return
    var names: PackedStringArray = player.get_animation_list()
    if names.size() < 1:
        reject("NATIVE_PLAYER_HAS_NO_IMPORTED_GLTF_ACTION")
        return
    var target_name: StringName = names[0]
    var animation: Animation = player.get_animation(target_name)
    if animation == null or animation.length <= 0:
        reject("INVALID_GLTF_CLIP_CLOCK")
        return
    var duration: float = animation.length
    if duration < 0.9 or duration > 1.4:
        reject("UNEXPECTED_GLTF_FPS_SOURCE_CLOCK " + str(duration))
        return
    var tracks: Array[Dictionary] = []
    for track_idx in range(animation.get_track_count()):
        tracks.append({"path": String(animation.track_get_path(track_idx)),
                       "type": animation.track_get_type(track_idx),
                       "keys": animation.track_get_key_count(track_idx)})
    print("R3_GODOT_TRACK_BINDING_DIAGNOSTIC ",JSON.stringify({
        "animation_name":String(target_name),
        "player_root_node":String(player.root_node),
        "skeleton_path":String(skeleton.get_path()),
        "skinned_mesh_path":String(mesh.get_path()),
        "bone_name":skeleton.get_bone_name(0),
        "rest_position":str(skeleton.get_bone_rest(0).origin),
        "tracks":tracks
    })
    player.play(target_name)
    player.seek(0.0, true)
    player.advance(0.0) # Explicit headless mix/evaluation after seek
    var start: Vector3 = skeleton.get_bone_global_pose(0).origin
    var start_local: Vector3 = skeleton.get_bone_pose_position(0)
    player.seek(duration, true)
    player.advance(0.0)
    var finish: Vector3 = skeleton.get_bone_global_pose(0).origin
    var finish_local: Vector3 = skeleton.get_bone_pose_position(0)
    print("R3_GODOT_BONE_TIME_DIAGNOSTIC ",JSON.stringify({
        "start_global":str(start),"end_global":str(finish),
        "start_local":str(start_local),"end_local":str(finish_local),
        "clip_length":duration,"currently_playing":String(player.current_animation)
    })
    var delta: Vector3 = finish - start
    if delta.length() < 0.5:
        reject("IMPORTED_SKELETON_BONE_MOTION_FROZEN " + str([start,finish,duration]))
        return
    var phases: Array[float] = [0.25,0.5,0.75]
    var expected: Array[float] = [0.25,0.5,0.75] if lane == "linear" else [0.6594358665676617,0.8710503045526693,0.9634757240065654]
    var observed: Array[float] = []
    var max_error: float = 0.0
    for i in range(phases.size()):
        player.seek(phases[i] * duration, true)
        player.advance(0.0)
        var pos: Vector3 = skeleton.get_bone_global_pose(0).origin
        var progress: float = (pos - start).dot(delta) / delta.length_squared()
        observed.append(progress)
        max_error = maxf(max_error, absf(progress - expected[i]))
    # Source had 1-unit total bone movement; imported time-resampled
    # animation is not an exact VMD authoring curve or facial morph/IK.
    if max_error > 0.012:
        reject("GLTF_TO_GODOT_TEMPORAL_MOTION_MISMATCH " + str([lane,observed,expected,max_error]))
        return
    print("R3_GODOT_INDEPENDENT_MOTION_RECEIPT ", JSON.stringify({
        "status": "PASS_INDEPENDENT_GODOT_GLTF_SYNTHETIC_ANIMATION_NARROW",
        "lane": lane,
        "engine": Engine.get_version_info().get("string","UNKNOWN"),
        "skeleton_bones": skeleton.get_bone_count(),
        "mesh_surfaces": mesh.mesh.get_surface_count(),
        "skin_binds": mesh.skin.get_bind_count(),
        "animation_tracks": animation.get_track_count(),
        "animation_seconds": duration,
        "sample_fractions": phases,
        "source_expected_progress": expected,
        "native_observed_progress": observed,
        "maximum_normalized_source_progress_error": max_error,
        "actual_bone_displacement": delta.length(),
        "vmd_bezier_source_controls": "NOT_PRESERVED_AS_VMD_NATIVE_CONTROLS",
        "vmd_morph_ik": "NOT_ADMITTED",
        "native_mmd_playback": "NOT_RUN",
        "MPFB_MHR": "NOT_RUN",
        "film": "HELD"
    }))
    scene.queue_free()
    quit(0)
