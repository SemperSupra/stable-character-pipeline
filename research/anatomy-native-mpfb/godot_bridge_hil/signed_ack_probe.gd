extends SceneTree
## R050 original-synthetic source-safe HMAC-authenticated Go plan and restart receipt.
## Integrity digest is SHA256, NOT authentication or cross-process ACID.

func hold(message: String) -> void:
    push_error("R049_GODOT_BRIDGE_HOLD " + message)
    quit(12)

func digest(raw: PackedByteArray, key: PackedByteArray) -> String:
    var mac: HMACContext = HMACContext.new()
    if mac.start(HashingContext.HASH_SHA256,key) != OK:
        return ""
    if mac.update(raw) != OK:
        return ""
    return mac.finish().hex_encode()

func write_checked(path: String, content: String) -> bool:
    var fp: FileAccess = FileAccess.open(path,FileAccess.WRITE)
    if fp == null:
        return false
    fp.store_string(content)
    fp.flush()
    fp.close()
    return true

func _initialize() -> void:
    var file_path: String = OS.get_environment("R049_SOURCE")
    if file_path.is_empty():
        file_path = "res://payload.json"
    var expected: String = FileAccess.get_file_as_string("res://sha256.txt").strip_edges()
    if expected.length() != 64:
        hold("missing or incorrect Go plan signature reference")
        return
    if not FileAccess.file_exists(file_path):
        hold("Go transaction source payload missing")
        return
    var actual: String = FileAccess.get_sha256(file_path)
    if actual != expected:
        hold("canonical payload digest mismatch: reject before any model mutation")
        return
    var private_hex: String = OS.get_environment("R050_HMAC_HEX_KEY")
    var key: PackedByteArray = private_hex.hex_decode()
    if key.size()!=32:
        hold("R050_EPHEMERAL_KEY_INVALID missing private runner 256-bit key")
        return
    var signed_raw: PackedByteArray = FileAccess.get_file_as_bytes(file_path)
    var tag: String = FileAccess.get_file_as_string("res://payload.hmac").strip_edges()
    if tag.length()!=64 or digest(signed_raw,key)!=tag:
        hold("R050_BAD_PLAN_HMAC reject unauthenticated payload before any model mutation")
        return
    var resumed: bool = false
    if FileAccess.file_exists("res://engine-ack.json"):
        if not FileAccess.file_exists("res://engine-ack.hmac"):
            hold("R050_ACK_SIGNATURE_MISSING incomplete previous commit")
            return
        var raw_ack: PackedByteArray = FileAccess.get_file_as_bytes("res://engine-ack.json")
        var old_mac: String = FileAccess.get_file_as_string("res://engine-ack.hmac").strip_edges()
        if old_mac.length()!=64 or digest(raw_ack,key)!=old_mac:
            hold("R050_BAD_ACK_HMAC reject modified restart checkpoint before any model mutation")
            return
        var prior = JSON.parse_string(raw_ack.get_string_from_utf8())
        if typeof(prior)!=TYPE_DICTIONARY:
            hold("R050_BAD_ACK_CHECKPOINT previous receipt is not a JSON object")
            return
        if prior.get("plan_sha256","")!=actual or int(prior.get("revision",-1))!=1 or int(prior.get("commands",-1))!=24:
            hold("R050_ACK_REVISION_HOLD conflicting or unsupported restart checkpoint")
            return
        resumed=true
    var document = JSON.parse_string(FileAccess.get_file_as_string(file_path))
    if typeof(document) != TYPE_DICTIONARY:
        hold("non-object canonical morph transaction")
        return
    var dict: Dictionary = document
    if dict.get("schema","") != "r048.morphcontrol.transaction.v1":
        hold("unexpected transaction schema")
        return
    if int(dict.get("expected_revision",-1)) != 0:
        hold("unexpected source model baseline revision")
        return
    var sequence: Array = dict.get("sequence",[])
    if sequence.size() != 24:
        hold("transaction does not include exactly 24 commands")
        return
    var packed: PackedScene = load("res://anchored.glb")
    if packed == null:
        hold("actual original synthetic shape-anchor GLB unavailable")
        return
    var scene: Node = packed.instantiate()
    get_root().add_child(scene)
    var skeletons: Array[Node] = scene.find_children("*","Skeleton3D",true,false)
    if skeletons.size() != 1 or (skeletons[0] as Skeleton3D).get_bone_count() != 163:
        hold("Godot imported original MPFB skeleton mismatch")
        return
    var target_names: PackedStringArray = PackedStringArray([
        "R043_EditableMask_MPFB_Body",
        "R045_AnchorSynthetic_Left",
        "R045_AnchorSynthetic_Right"])
    var meshes: Array[MeshInstance3D] = []
    var nodes: Array[Node] = scene.find_children("*","MeshInstance3D",true,false)
    for expected_name: String in target_names:
        var found: MeshInstance3D = null
        for n: Node in nodes:
            var m: MeshInstance3D = n as MeshInstance3D
            if String(m.name).contains(expected_name):
                if found != null:
                    hold("duplicated target mesh " + expected_name)
                    return
                found = m
        if found == null or found.mesh == null or found.skin == null:
            hold("named target mesh lacks source morph surface/skin " + expected_name)
            return
        if found.mesh.get_blend_shape_count() != 8:
            hold("target morph channel count differs " + expected_name)
            return
        meshes.append(found)
    if meshes.size() != 3:
        hold("incomplete source shape target set")
        return

    # Stage ALL operations and verify canonical matrix, target/index/name,
    # finite bounded values and cross-target consistency BEFORE any writes.
    var staged: Array[Dictionary] = []
    var named_channels: Array[String] = []
    var values: Array[float] = []
    for i in range(sequence.size()):
        if typeof(sequence[i]) != TYPE_DICTIONARY:
            hold("malformed individual Go morph command")
            return
        var command: Dictionary = sequence[i]
        var ti: int = i / 8
        var ki: int = i % 8
        var name: String = String(command.get("channel",""))
        var target: String = String(command.get("target",""))
        var index: int = int(command.get("index",-1))
        var value: float = float(command.get("value",NAN))
        if target != target_names[ti] or index != ki:
            hold("target order/index mismatch in canonical plan")
            return
        if not is_finite(value) or value < -1.0 or value > 1.0:
            hold("nonfinite or out-of-range canonical morph")
            return
        if ti == 0:
            named_channels.append(name)
            values.append(value)
        elif named_channels[ki] != name or absf(values[ki]-value) > 0.0000001:
            hold("inconsistent synchronized source morph commands")
            return
        if String(meshes[ti].mesh.get_blend_shape_name(ki)) != name:
            hold("Go canonical morph name does not match actual Godot imported channel")
            return
        staged.append({"target":ti,"index":ki,"value":value})
    if staged.size()!=24:
        hold("staging truncated morph plan")
        return

    var before: Array[float] = []
    for item: Dictionary in staged:
        before.append(meshes[int(item["target"])].get_blend_shape_value(int(item["index"])))
    var applied: int = 0
    var failed: bool = false
    for item: Dictionary in staged:
        var obj: MeshInstance3D = meshes[int(item["target"])]
        var index: int = int(item["index"])
        var value: float = float(item["value"])
        obj.set_blend_shape_value(index,value)
        if absf(obj.get_blend_shape_value(index)-value) > 0.00001:
            failed = true
            break
        applied += 1
    if failed:
        # Compensating rollback is a local best-effort policy, not a
        # cross-process transactional guarantee.
        for i in range(staged.size()):
            var item: Dictionary = staged[i]
            meshes[int(item["target"])].set_blend_shape_value(int(item["index"]),before[i])
        hold("Godot runtime rejected morph command; attempted local rollback")
        return

    var observed: Array[float] = []
    for item: Dictionary in staged:
        observed.append(meshes[int(item["target"])].get_blend_shape_value(int(item["index"])))
    if observed.size()!=24:
        hold("R050_ENGINE_OBSERVED_VALUES_MISSING")
        return
    var ack: Dictionary = {
        "schema":"r050.godot.engine-ack.v1",
        "status":"ENGINE_ACK_APPLIED_AND_READ_BACK",
        "plan_sha256":actual,
        "revision":1,
        "previous_revision":0,
        "commands":24,
        "targets":3,
        "channels_per_target":8,
        "values":observed,
        "restart_rehydration":resumed,
        "godot_version":Engine.get_version_info().get("string","UNKNOWN")
    }
    var ack_json: String = JSON.stringify(ack)
    var ack_mac: String = digest(ack_json.to_utf8_buffer(),key)
    if ack_mac.length()!=64:
        hold("R050_ACK_MAC_FAILURE")
        return
    if not write_checked("res://engine-ack.pending.json",ack_json):
        hold("R050_ACK_WRITE_ERROR cannot write pending receipt")
        return
    if not write_checked("res://engine-ack.pending.hmac",ack_mac):
        hold("R050_ACK_WRITE_ERROR cannot write pending HMAC")
        return
    var root_path: String = ProjectSettings.globalize_path("res://")
    if DirAccess.rename_absolute(root_path.path_join("engine-ack.pending.json"),
                                 root_path.path_join("engine-ack.json"))!=OK:
        hold("R050_ACK_RENAME_FAILURE cannot commit engine receipt")
        return
    if DirAccess.rename_absolute(root_path.path_join("engine-ack.pending.hmac"),
                                 root_path.path_join("engine-ack.hmac"))!=OK:
        hold("R050_ACK_RENAME_FAILURE cannot commit HMAC companion")
        return
    if FileAccess.get_sha256("res://engine-ack.json").length()!=64:
        hold("R050_ACK_PERSISTENCE_HOLD receipt reopen failed")
        return
    print("R050_GODOT_SIGNED_ACK_RECEIPT ",JSON.stringify({
        "status":"PASS_NARROW_AUTHENTICATED_LOCAL_ENGINE_ACK_AND_REHYDRATION",
        "plan_sha256":actual,
        "ack_file_sha256":FileAccess.get_sha256("res://engine-ack.json"),
        "commands":applied,
        "engine":Engine.get_version_info().get("string","UNKNOWN"),
        "restart_rehydration":resumed,
        "limits":"Ephemeral runner key, local checkpoint and restart state only; no external identity authority or cross-process ACID"
    }))

    print("R049_GODOT_BRIDGE_RECEIPT ",JSON.stringify({
        "schema":"r049.morphcontrol.godot-bridge.v1",
        "status":"PASS_NARROW_GO_CANONICAL_PLAN_APPLIED_TO_GODOT_MORPH_STATE",
        "godot_engine":Engine.get_version_info().get("string","UNKNOWN"),
        "canonical_payload_sha256":actual,
        "godot_accepted_revision":0,
        "explicitly_applied_commands":applied,
        "source_bone_count":163,
        "mesh_targets":meshes.size(),
        "morph_channels_per_mesh":8,
        "all_staged_before_mutation":true,
        "limits":"No authentic signed plan, no durable engine acknowledgments, no cross-process ACID, GPU vertex parity, genuine organs, real character, photorealism or film acceptance"
    }))
    scene.queue_free()
    quit(0)
