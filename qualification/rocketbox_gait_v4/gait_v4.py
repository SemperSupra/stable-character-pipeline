"""R009 MIT measured native local-Z leg motion/park corrective V3.

This code is NOT a foot-contact solver, anatomical coordinate calibration or
product-quality certification. All 72 frames are authored from a frozen MIT rig.
The protected Naomi/Alison assets, private runners and source are not inputs.
"""
from __future__ import annotations
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "rocketbox_park"))
from park_72f import (ACTORS, SOURCE_BLEND_SHA, SOURCE_COMMIT, FRAMES, FPS,
                       compose_park, camera_ortho_scale, sha256_bytes, native_run)

CYCLES = 3.2
LEG_AXIS = "Z"  # native 24-axis foot-mesh probe: Z yields actual world-X skin motion
AXIS_PROBE_ZIP_SHA256 = "585f50e4d9acacaf63557098287c9caec110dbc000fae5934941eb090369b5ce"
SCHEMA = "scp.r009.mit_original_gait_v4_park72.v1"
BONES = (
    "Bip01 L Thigh", "Bip01 R Thigh", "Bip01 L Calf", "Bip01 R Calf",
    "Bip01 L UpperArm", "Bip01 R UpperArm",
    "Bip01 L Forearm", "Bip01 R Forearm",
    "Bip01 L Foot", "Bip01 R Foot",
)


LEG_BONES = frozenset(name for name in BONES if name.endswith(("Thigh", "Calf", "Foot")))


def pose_at(frame, actor):
    """Independent pure source timeline, no solver/ground-contact claims."""
    if type(frame) is not int or not 0 <= frame < FRAMES or type(actor) is not int or actor not in (0, 1):
        raise ValueError("INVALID_FRAME_ACTOR")
    u = frame / (FRAMES - 1)
    travel = u * u * (3.0 - 2.0 * u)
    fade = min(1.0, 8.0*u, 8.0*(1.0-u))
    phase = 2.0*math.pi*CYCLES*travel + actor*.30
    s = math.sin(phase)
    x = (-2.9 + 2.05*travel) if actor == 0 else (2.9 - 2.05*travel)
    angles = {
        "Bip01 L Thigh": .25*fade*s,
        "Bip01 R Thigh": -.25*fade*s,
        "Bip01 L Calf": .08 + .28*fade*max(0., s),
        "Bip01 R Calf": .08 + .28*fade*max(0., -s),
        "Bip01 L UpperArm": -.29*fade*s,
        "Bip01 R UpperArm": .29*fade*s,
        "Bip01 L Forearm": .13 + .07*fade*s,
        "Bip01 R Forearm": .13 - .07*fade*s,
        "Bip01 L Foot": -.10*fade*s,
        "Bip01 R Foot": .10*fade*s,
    }
    if tuple(angles) != BONES or not all(math.isfinite(v) for v in (x, *angles.values())):
        raise RuntimeError("MOTION_SOURCE_NONFINITE_OR_INCOMPLETE")
    return x, angles


def find_native_armatures(bpy):
    out = []
    if len(ACTORS) != 2:
        raise RuntimeError("SOURCE_ACTOR_CARDINALITY")
    for rootname in ACTORS:
        root = bpy.data.objects.get(rootname)
        if root is None or root.type != "EMPTY":
            raise RuntimeError("SOURCE_NATIVE_ROOT_MISSING:" + rootname)
        arms = [o for o in bpy.data.objects if o.type == "ARMATURE" and
                (o.parent == root or o.parent is not None and o.parent.parent == root)]
        if len(arms) != 1 or len(arms[0].data.bones) != 80:
            raise RuntimeError("SOURCE_NATIVE_80_BONE_OWNER_MISMATCH:" + rootname)
        arm = arms[0]
        for name in BONES:
            if arm.pose.bones.get(name) is None:
                raise RuntimeError("SOURCE_BONE_MISSING:" + rootname + ":" + name)
        out.append((root, arm))
    return out


def author_source_keys(bpy, actors):
    for actor_index, (root, arm) in enumerate(actors):
        root.rotation_mode = "XYZ"
        for name in BONES:
            arm.pose.bones[name].rotation_mode = "XYZ"
        for frame in range(FRAMES):
            x, vals = pose_at(frame, actor_index)
            root.location.x = x
            root.keyframe_insert(data_path="location", frame=frame, group="SourceOriginalGaitV2")
            for name in BONES:
                bone = arm.pose.bones[name]
                if name in LEG_BONES:
                    # Real 24-axis evaluated MIT foot-skin observer measured
                    # local Z as world-approach leg influence, unlike source X.
                    # Cancel old X leg swing; never compound both source paths.
                    bone.rotation_euler.x = 0.0
                    bone.rotation_euler.z = vals[name]
                else:
                    bone.rotation_euler.x = vals[name]
                bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=name)
    # Reevaluate real native pose at every tick; do not trust self-reported keys as skin/foot evidence.
    observed = []
    for frame in range(FRAMES):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        roots = [float(root.matrix_world.translation.x) for root, _ in actors]
        if not all(math.isfinite(v) for v in roots):
            raise RuntimeError("NATIVE_NONFINITE_ROOT")
        observed.append({"frame": frame, "root_world_x": roots})
    if not (observed[0]["root_world_x"][0] < observed[-1]["root_world_x"][0] and
            observed[0]["root_world_x"][1] > observed[-1]["root_world_x"][1]):
        raise RuntimeError("SOURCE_NATIVE_ROOT_CONVERGENCE_NOT_OBSERVED")
    return observed



def feedback_root_path(rows, direction, path_top):
    """Original source evaluated foot positions guide a candidate root easing.

    Does not identify force/stance; near-ground is an engineering heuristic.
    The root moves monotonically, and exact desired terminal separation remains.
    """
    if len(rows) != FRAMES or direction not in (-1, 1) or not math.isfinite(path_top):
        raise ValueError("FEEDBACK_INPUT_OR_CLOCK")
    raw=[]
    selected=[]
    for tick in range(1, FRAMES):
        a, b = rows[tick-1], rows[tick]
        nominal = direction * (b["root_x"]-a["root_x"])
        if not math.isfinite(nominal) or not -.000001 <= nominal <= .20:
            raise ValueError("INVALID_NOMINAL_NATIVE_SOURCE_ROOT")
        candidates=[]
        for side in ("L","R"):
            prior, curr = a[side], b[side]
            if not all(math.isfinite(v) for v in (prior["x"],prior["z"],curr["x"],curr["z"])):
                raise ValueError("NONFINITE_SOURCE_WEIGHTED_FOOT")
            if max(prior["z"],curr["z"]) <= path_top+.05:
                prior_rel=prior["x"]-a["root_x"]
                curr_rel=curr["x"]-b["root_x"]
                needed=-direction*(curr_rel-prior_rel)
                if .000001 < needed < .18:
                    candidates.append((max(prior["z"],curr["z"]),side,needed))
        if candidates:
            _,side,needed=min(candidates)
            step=.60*needed+.40*max(0.,nominal)
            selected.append(side)
        else:
            step=max(0.,nominal)
            selected.append("NONE")
        raw.append(min(.16,max(.000001,step)))
    if sum(raw)<.2 or sum(raw)>8.0:
        raise ValueError("UNBOUNDED_FEEDBACK_PROGRESS")
    smooth=[(.20*raw[max(0,i-1)]+.60*raw[i]+.20*raw[min(len(raw)-1,i+1)])
            for i in range(len(raw))]
    scalar=2.05/sum(smooth)
    if not .25<=scalar<=4.0:
        raise ValueError("ROOT_PROGRESS_NORMALIZATION_UNBOUNDED")
    roots=[rows[0]["root_x"]]
    for step in smooth:
        roots.append(roots[-1]+direction*step*scalar)
    if not all(math.isfinite(v) for v in roots):
        raise ValueError("FEEDBACK_NONFINITE")
    if any(direction*(roots[i+1]-roots[i])<=0 for i in range(71)):
        raise ValueError("FEEDBACK_NOT_MONOTONE")
    if abs(direction*(roots[-1]-roots[0])-2.05)>1e-5:
        raise ValueError("FEEDBACK_ENDPOINT_MISMATCH")
    return roots, {"chosen_proxy_foot_by_interval":selected,
                   "normalization":round(scalar,6),
                   "raw_progress_m":round(sum(raw),6),
                   "native_weighted_skin_foot_contact":"UNKNOWN",
                   "physics_contact_certified":False}


def native_feedback_correction(bpy, actors):
    """Read genuine weighted foot skin and key a new root schedule only."""
    from mathutils import Vector
    walkway=bpy.data.objects.get("OriginalPark_Walkway")
    if walkway is None or walkway.type!="MESH":
        raise RuntimeError("SOURCE_OWNED_GROUND_NOT_FOUND")
    path_top=max((walkway.matrix_world@Vector(v)).z for v in walkway.bound_box)
    if not math.isfinite(path_top):
        raise RuntimeError("SOURCE_OWNED_GROUND_NONFINITE")
    selections={}
    for root,arm in actors:
        mesh=[o for o in bpy.data.objects if o.type=="MESH" and
              any(m.type=="ARMATURE" and m.object==arm for m in o.modifiers)]
        if len(mesh)!=1:raise RuntimeError("SOURCE_WEIGHTED_SKIN_AMBIGUOUS:"+root.name)
        ob=mesh[0]
        names={g.name:g.index for g in ob.vertex_groups}
        selected={}
        for side in ("L","R"):
            wanted=(f"Bip01 {side} Foot", f"Bip01 {side} Toe0")
            if any(name not in names for name in wanted):
                raise RuntimeError("SOURCE_FOOT_GROUP_MISSING:"+root.name+":"+side)
            ids={names[name] for name in wanted}
            verts=[v.index for v in ob.data.vertices if
                   sum(g.weight for g in v.groups if g.group in ids)>=.50]
            if len(verts)<12:raise RuntimeError("SOURCE_FOOT_SKIN_POPULATION_MISSING")
            selected[side]=verts
        selections[root.name]=(ob,selected)
    data={root.name:[] for root,_ in actors}
    for frame in range(FRAMES):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        deps=bpy.context.evaluated_depsgraph_get()
        for root,_ in actors:
            mesh,ids=selections[root.name]
            ev=mesh.evaluated_get(deps)
            obj=ev.to_mesh()
            try:
                if len(obj.vertices)!=len(mesh.data.vertices):
                    raise RuntimeError("SOURCE_EVALUATED_TOPOLOGY_CHANGED")
                rec={"root_x":float(root.matrix_world.translation.x)}
                for side,indices in ids.items():
                    pts=[ev.matrix_world@obj.vertices[i].co for i in indices]
                    rec[side]={"x":sum(v.x for v in pts)/len(pts),
                               "z":min(v.z for v in pts)}
                data[root.name].append(rec)
            finally:
                ev.to_mesh_clear()
    diagnostics={"path_top_m":float(path_top),"by_actor":{}}
    for actor,(root,_) in enumerate(actors):
        old=data[root.name]
        direction=1 if actor==0 else -1
        output,rec=feedback_root_path(old,direction,float(path_top))
        for frame,x in enumerate(output):
            bpy.context.scene.frame_set(frame)
            root.location.x=x
            root.keyframe_insert(data_path="location",frame=frame,group="NativeFootFeedbackV4")
        diagnostics["by_actor"][root.name]={**rec,
            "old_terminal_world_x":old[-1]["root_x"],
            "feedback_terminal_world_x":output[-1],
            "source_weighted_foot_population":{side:len(ids) for side,ids in selections[root.name][1].items()}}
    final=[]
    for frame in range(FRAMES):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        final.append({"frame":frame,"root_world_x":[float(root.matrix_world.translation.x) for root,_ in actors]})
    if final[0]["root_world_x"][0]>=final[-1]["root_world_x"][0] or final[0]["root_world_x"][1]<=final[-1]["root_world_x"][1]:
        raise RuntimeError("V4_NATIVE_ROOTS_NOT_CONVERGING")
    return final,diagnostics


def run(src, tex, output):
    import bpy
    from mathutils import Vector

    output.mkdir(parents=True, exist_ok=True)
    # Original exact-source SHA and all six source MIT TGA Git blob/UV/opacity
    # tests are executed by unchanged material source owner before this overlay.
    native_run(src, tex, output / "source-material-preflight")
    previous = json.loads((output/"source-material-preflight"/"native_material_uv_receipt.json").read_text())
    if previous.get("uv_assignment") != "SOURCE_LABELED_MIT_BODY_HEAD_OPACITY_BINDING_VERIFIED":
        raise RuntimeError("FROZEN_MIT_MATERIAL_SOURCE_NOT_VERIFIED")
    scene = bpy.context.scene
    if (scene.frame_start, scene.frame_end, scene.render.fps) != (0, 71, 12):
        raise RuntimeError("SOURCE_NATIVE_CLOCK_MISMATCH")
    actors = find_native_armatures(bpy)
    observed = author_source_keys(bpy, actors)
    park = compose_park(bpy)
    observed, foot_feedback = native_feedback_correction(bpy,actors)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 4
    scene.render.resolution_x = 480
    scene.render.resolution_y = 270
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.camera.data.type = "ORTHO"
    report = {
        "schema": SCHEMA, "status": "SOURCE_NATIVE_FOOT_FEEDBACK_V4_TWO_VIEW_RESEARCH_CANDIDATE",
        "source_blend_sha256": SOURCE_BLEND_SHA,
        "source_commit": SOURCE_COMMIT, "source_rights": "MICROSOFT_ROCKETBOX_MIT_WITH_NOTICE",
        "gait_source": "ORIGINAL_NATIVE_MIT_LOCAL_Z_FOOT_FEEDBACK_RESEARCH_CANDIDATE",
        "source_native_axis_probe_zip_sha256": AXIS_PROBE_ZIP_SHA256,
        "calibration_source_local_Z_world_X_preference": "OBSERVED_WEIGHTED_SKIN_ONLY_NOT_BIOMECHANICAL_SIGNED_JCS",
        "bone_rest_axis_calibrated": False, "true_foot_contact": "UNKNOWN",
        "signed_human_rom": "NOT_RUN", "realistic_human_gait": "UNKNOWN",
        "independent_human_visual_acceptance": "NOT_RUN",
        "original_naomi_alison_mvp_accepted": False, "product_accepted": False,
        "frames": FRAMES, "fps": FPS, "actor_roots": list(ACTORS),
        "source_materials": "SIX_ORIGINAL_MIT_TGAS_BINDING_VERIFIED",
        "procedural_scene": park, "native_observed_root_x_all72": observed,
        "native_source_sole_feedback_diagnostics": foot_feedback,
        "views": {},
    }
    receipt = output/"park_render_receipt.json"
    def save():
        receipt.write_text(json.dumps(report, sort_keys=True, indent=2, allow_nan=False)+"\n")
    save()
    for view, loc in (("front", (0., -10., 2.5)), ("oblique", (2.6, -9.5, 3.0))):
        scene.camera.location = loc
        scene.camera.rotation_euler = (Vector((0,0,1.12))-scene.camera.location).to_track_quat("-Z","Y").to_euler()
        dest = output/view
        dest.mkdir(exist_ok=True)
        hashes, scales = [], []
        for frame in range(FRAMES):
            scene.frame_set(frame)
            scene.camera.data.ortho_scale = camera_ortho_scale(frame)
            scales.append(float(scene.camera.data.ortho_scale))
            filepath = dest/("frame_%03d.png" % frame)
            scene.render.filepath = str(filepath)
            bpy.ops.render.render(write_still=True)
            raw = filepath.read_bytes()
            if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
                raise RuntimeError("NATIVE_FRAME_PNG_INVALID:"+view+":"+str(frame))
            hashes.append(sha256_bytes(raw))
        report["views"][view] = {
            "camera": list(loc), "native_frame_count": len(hashes),
            "all72_native_png_hashes": hashes,
            "all72_source_authored_camera_scales": scales,
        }
        save()
    print(json.dumps({"status": report["status"],
                      "frames": FRAMES, "views": list(report["views"]),
                      "true_foot_contact": "UNKNOWN", "product_accepted": False}))


if __name__ == "__main__":
    if "--" not in sys.argv:
        raise RuntimeError("ARGS_REQUIRED")
    args = sys.argv[sys.argv.index("--")+1:]
    if len(args) != 3:
        raise RuntimeError("USAGE original.blend original-mit-six-tga-dir output-dir")
    run(*(Path(p).resolve() for p in args))
