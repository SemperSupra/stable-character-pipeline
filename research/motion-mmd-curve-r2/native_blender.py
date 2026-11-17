#!/usr/bin/env python3
"""Original synthetic VMD curve -> actual Blender bpy pose and evaluated skin.
Real pinned MMD Tools importer. No MMD runtime, real person, or production rig.
"""
import argparse, contextlib, importlib.util, json, math, os, pathlib, sys, tempfile

def run(root, lane):
    import bpy
    assert bpy.app.version >= (4,2,0)
    import mathutils
    import probe as src
    srcroot = root.resolve()
    vmdmod = src.upstream(srcroot)
    curve = src.CURVE if lane=="nonlinear" else src.LINEAR
    with tempfile.TemporaryDirectory(prefix="original-native-vmd-") as tmp:
        p=pathlib.Path(tmp)/"original.vmd"
        src.authored(vmdmod,p,curve=curve)
        motion=src.loaded(vmdmod,p)
        src.check_strict_semantics(motion,curve=curve)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sys.path.insert(0,str(srcroot))
        from mmd_tools.core.vmd.importer import VMDImporter
        ad=bpy.data.armatures.new("R2_Original_Synthetic_Armature")
        arm=bpy.data.objects.new("R2_Original_Synthetic_Rig",ad)
        bpy.context.scene.collection.objects.link(arm)
        bpy.context.view_layer.objects.active=arm
        arm.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        b=ad.edit_bones.new(src.NAME)
        b.head=(0,0,0)
        b.tail=(0,0,.5)
        bpy.ops.object.mode_set(mode="OBJECT")
        bone=arm.pose.bones[src.NAME]
        bone.rotation_mode="QUATERNION"
        me=bpy.data.meshes.new("original_abstract_quad")
        me.from_pydata([(0,0,0),(.2,0,0),(.2,.2,0),(0,.2,0)],[],[(0,1,2,3)])
        ob=bpy.data.objects.new("original_syn_skin",me)
        bpy.context.scene.collection.objects.link(ob)
        vg=ob.vertex_groups.new(name=src.NAME)
        vg.add([0,1,2,3],1.0,"REPLACE")
        modifier=ob.modifiers.new("source_native_armature","ARMATURE")
        modifier.object=arm
        VMDImporter(str(p),scale=1.0,frame_margin=0).assign(arm)
        assert arm.animation_data and arm.animation_data.action
        def sample(tick):
            whole=int(math.floor(tick))
            frac=tick-whole
            bpy.context.scene.frame_set(whole,subframe=frac)
            bpy.context.view_layer.update()
            loc=mathutils.Vector(bone.location)
            eval_ob=ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
            mesh=eval_ob.to_mesh()
            try:
                world=eval_ob.matrix_world@mesh.vertices[0].co
                return loc.copy(),world.copy()
            finally:
                eval_ob.to_mesh_clear()
        start, vstart=sample(0)
        finish, vfinish=sample(30)
        delta=finish-start
        skin_delta=vfinish-vstart
        assert delta.length>.5, "upstream bone translation frozen"
        assert skin_delta.length>.5, "actually evaluated skinned vertex frozen"
        den=delta.length_squared
        observed={}
        expected={}
        maxres=0.0
        for tick in (7.5,15.0,22.5):
            loc,v=sample(tick)
            alpha=(loc-start).dot(delta)/den
            expected_alpha=src.curve_at(tick/30.0,curve)
            observed[str(tick)]=alpha
            expected[str(tick)]=expected_alpha
            # Compare at real subframes, not only 0 / 30.
            maxres=max(maxres,abs(alpha-expected_alpha))
            # Require skin following actual evaluated animation, not armature-only.
            skin_alpha=(v-vstart).dot(skin_delta)/skin_delta.length_squared
            assert abs(skin_alpha-alpha)<.01, "skinned native vertex failed to follow bone"
        s0, z0=sample(0)
        assert (s0-start).length<1e-7 and (z0-vstart).length<1e-7
        # Blender interpolation handles should faithfully approximate authored MMD curve.
        assert maxres <= .04, ("native interpolation mismatch",maxres,observed,expected)
        report={"status":"PASS_NATIVE_BLENDER_SOURCE_SYNTHETIC_BONE_SKIN_CURVE",
                "lane":lane,"actual_blender":bpy.app.version_string,
                "vendor_commit":src.UPSTREAM,
                "original_vmd_sha256":__import__("hashlib").sha256(p.read_bytes()).hexdigest(),
                "native_frame_samples":observed,"vmd_mathematical_samples":expected,
                "max_unit_curve_difference":maxres,"bone_displacement_units":delta.length,
                "skin_vertex_displacement_units":skin_delta.length,
                "sampled_subframes":[7.5,15,22.5],
                "source_class":"SELF_AUTHORED_SYNTHETIC",
                "true_MMD_runtime":"NOT_RUN",
                "morph_ik_evaluated":"NOT_QUALIFIED",
                "MPFB_MHR_retarget":"NOT_RUN",
                "production_human":"HOLD"}
        print(json.dumps(report,sort_keys=True),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",type=pathlib.Path,required=True)
    p.add_argument("--lane",choices=("nonlinear","linear"),required=True)
    a=p.parse_args()
    run(a.upstream,a.lane)
    sys.stdout.flush();sys.stderr.flush()
    # Prior source-native Blender Python-wheel process hung on interpreter shutdown.
    os._exit(0)
