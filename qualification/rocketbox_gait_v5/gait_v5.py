"""R009 MIT measured native stance-Jacobian leg motion/park corrective V5.

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
SCHEMA = "scp.r009.mit_original_gait_v5_park72.v1"
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



def damped_joint_update(jacobian, error, damping=.035, limit=.09):
    """Bounded two-joint 2D regularized Jacobian inverse; *not* anatomical IK."""
    if (len(jacobian)!=2 or any(len(row)!=2 for row in jacobian) or
        len(error)!=2 or type(damping) not in (int,float) or
        type(limit) not in (int,float)):
        raise ValueError("BAD_STANCE_JACOBIAN_SHAPE")
    vals=[*jacobian[0],*jacobian[1],*error,damping,limit]
    if not all(math.isfinite(v) for v in vals) or damping<=0 or not 0<limit<=.25:
        raise ValueError("INVALID_STANCE_JACOBIAN_OR_BOUND")
    (j00,j01),(j10,j11)=jacobian
    a=j00*j00+j10*j10+damping*damping
    b=j00*j01+j10*j11
    c=j01*j01+j11*j11+damping*damping
    det=a*c-b*b
    if not math.isfinite(det) or det<=0:
        raise RuntimeError("SINGULAR_DAMPED_JACOBIAN")
    e0=j00*error[0]+j10*error[1]
    e1=j01*error[0]+j11*error[1]
    o0=(c*e0-b*e1)/det
    o1=(a*e1-b*e0)/det
    return tuple(max(-limit,min(limit,v)) for v in (o0,o1))


def apply_native_stance_jacobian(bpy, actors):
    """Author-candidate per-frame local Z thigh/calf correction from source skin.

    Only a near-floor *proxy* selects a tentative stance foot, not actual force/
    toe-contact. The generated report is PRODUCER SELF-DIAGNOSTIC, not an independent
    sole observer, and must be independently measured before any promotion.
    """
    from mathutils import Vector
    walkway=bpy.data.objects.get("OriginalPark_Walkway")
    if walkway is None or walkway.type!="MESH":
        raise RuntimeError("V5_SOURCE_WALKWAY_MISSING")
    path_top=max((walkway.matrix_world @ Vector(v)).z for v in walkway.bound_box)
    if not math.isfinite(path_top):
        raise RuntimeError("V5_SOURCE_WALKWAY_NONFINITE")
    weights={}
    for root,arm in actors:
        matching=[ob for ob in bpy.data.objects if ob.type=="MESH" and
                  any(m.type=="ARMATURE" and m.object==arm for m in ob.modifiers)]
        if len(matching)!=1:raise RuntimeError("V5_SOURCE_SKIN_AMBIGUOUS:"+root.name)
        ob=matching[0]; names={g.name:g.index for g in ob.vertex_groups}
        sides={}
        for side in ("L","R"):
            wanted=(f"Bip01 {side} Foot",f"Bip01 {side} Toe0")
            if any(w not in names for w in wanted):
                raise RuntimeError("V5_SOURCE_FOOT_GROUP_MISSING:"+root.name+":"+side)
            groups={names[w] for w in wanted}
            ids=[v.index for v in ob.data.vertices
                 if sum(g.weight for g in v.groups if g.group in groups)>=.5]
            if len(ids)<12:raise RuntimeError("V5_WEIGHTED_FOOT_POPULATION_MISSING")
            sides[side]=ids
        weights[root.name]=(ob,sides)
    def sole(ob,ids):
        bpy.context.view_layer.update()
        deps=bpy.context.evaluated_depsgraph_get()
        ev=ob.evaluated_get(deps); mesh=ev.to_mesh()
        try:
            if len(mesh.vertices)!=len(ob.data.vertices):
                raise RuntimeError("V5_NATIVE_TOPOLOGY_CHANGED")
            pts=[ev.matrix_world@mesh.vertices[i].co for i in ids]
            x=sum(p.x for p in pts)/len(pts); z=min(p.z for p in pts)
            if not (math.isfinite(x) and math.isfinite(z)):
                raise RuntimeError("V5_SOURCE_NONFINITE_WEIGHTED_SOLE")
            return x,z
        finally:ev.to_mesh_clear()
    results={root.name:{"frames":[],"weighted_foot_vertices":
                         {s:len(ids) for s,ids in weights[root.name][1].items()},
                         "source_measured_only_not_independent":True}
             for root,_ in actors}
    state={root.name:{"side":None,"anchor_x":None} for root,_ in actors}
    for frame in range(FRAMES):
        bpy.context.scene.frame_set(frame)
        for root,arm in actors:
            ob,sides=weights[root.name]
            baseline={s:sole(ob,ids) for s,ids in sides.items()}
            eligible=[s for s in ("L","R") if baseline[s][1]<=path_top+.05]
            current=state[root.name]["side"]
            if current in eligible and (len(eligible)==1 or
                    baseline[current][1]<=min(baseline[s][1] for s in eligible)+.025):
                chosen=current
            else:
                chosen=min(eligible,key=lambda s:baseline[s][1]) if eligible else None
            if chosen is None:
                state[root.name]={"side":None,"anchor_x":None}
                results[root.name]["frames"].append({"frame":frame,"selected":"NONE"})
                continue
            if chosen!=current:
                state[root.name]={"side":chosen,"anchor_x":baseline[chosen][0]}
            anchor=state[root.name]["anchor_x"]
            target_z=min(path_top+.028,max(path_top+.007,baseline[chosen][1]))
            bones=[arm.pose.bones[f"Bip01 {chosen} {part}"] for part in ("Thigh","Calf")]
            originals=[float(b.rotation_euler.z) for b in bones]
            pre=baseline[chosen]
            iterations=0
            for _ in range(4):
                x,z=sole(ob,sides[chosen])
                err=(anchor-x,target_z-z)
                if abs(err[0])<.008 and abs(err[1])<.012:break
                jaccols=[]
                for b in bones:
                    angle=float(b.rotation_euler.z)
                    b.rotation_euler.z=angle+.018
                    px,pz=sole(ob,sides[chosen])
                    b.rotation_euler.z=angle
                    jaccols.append(((px-x)/.018,(pz-z)/.018))
                bpy.context.view_layer.update()
                jac=((jaccols[0][0],jaccols[1][0]),
                     (jaccols[0][1],jaccols[1][1]))
                deltas=damped_joint_update(jac,err)
                for bone,original,step in zip(bones,originals,deltas):
                    bone.rotation_euler.z=max(original-.36,min(original+.36,
                                           float(bone.rotation_euler.z)+step))
                bpy.context.view_layer.update();iterations+=1
            post=sole(ob,sides[chosen])
            for bone in bones:
                bone.keyframe_insert(data_path="rotation_euler",frame=frame,group=bone.name)
            results[root.name]["frames"].append({
                "frame":frame,"selected":chosen,"producer_iterations":iterations,
                "initial_sole_x_m":round(pre[0],6),
                "initial_min_z_m":round(pre[1],6),
                "final_sole_x_m":round(post[0],6),
                "final_min_z_m":round(post[1],6),
                "anchor_x_m":round(anchor,6),
                "stance_x_residual_m":round(abs(post[0]-anchor),6),
                "stance_z_residual_m":round(abs(post[1]-target_z),6),
                "local_z_correction_rad":[round(float(b.rotation_euler.z)-orig,6)
                    for b,orig in zip(bones,originals)]})
    return {"source_ground_top_z_m":path_top,
            "producer_self_diagnostic_only":True,
            "physical_contact_certified":False,
            "ik_anatomical_certified":False,
            "by_actor":results}


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
    stance = apply_native_stance_jacobian(bpy,actors)
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
        "schema": SCHEMA, "status": "SOURCE_NATIVE_SOURCE_NATIVE_STANCE_JACOBIAN_V5_TWO_VIEW_RESEARCH_CANDIDATE",
        "source_blend_sha256": SOURCE_BLEND_SHA,
        "source_commit": SOURCE_COMMIT, "source_rights": "MICROSOFT_ROCKETBOX_MIT_WITH_NOTICE",
        "gait_source": "ORIGINAL_NATIVE_MIT_STANCE_JACOBIAN_RESEARCH_CANDIDATE",
        "source_native_axis_probe_zip_sha256": AXIS_PROBE_ZIP_SHA256,
        "calibration_source_local_Z_world_X_preference": "OBSERVED_WEIGHTED_SKIN_ONLY_NOT_BIOMECHANICAL_SIGNED_JCS",
        "bone_rest_axis_calibrated": False, "true_foot_contact": "UNKNOWN",
        "signed_human_rom": "NOT_RUN", "realistic_human_gait": "UNKNOWN",
        "independent_human_visual_acceptance": "NOT_RUN",
        "original_naomi_alison_mvp_accepted": False, "product_accepted": False,
        "frames": FRAMES, "fps": FPS, "actor_roots": list(ACTORS),
        "source_materials": "SIX_ORIGINAL_MIT_TGAS_BINDING_VERIFIED",
        "procedural_scene": park, "native_observed_root_x_all72": observed,
        "stance_candidate_source_diagnostics": stance,
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
