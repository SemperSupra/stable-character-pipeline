#!/usr/bin/env python3
"""Real VMD->MMD Tools->Blender skin->GLB->Blender roundtrip, original fixture only.

Only ephemeral first-party synthetic mesh/VMD are generated; no person/model media.
"""
import argparse, hashlib, json, math, os, pathlib, struct, sys, tempfile, traceback

def fail(msg):
    raise AssertionError(msg)

def skin_state(bpy, obj, time):
    scene=bpy.context.scene
    scene.frame_set(int(math.floor(time)),subframe=time-math.floor(time))
    bpy.context.view_layer.update()
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evaluated.to_mesh()
    try:
        verts=[evaluated.matrix_world@v.co for v in mesh.vertices]
        if not verts: fail("EMPTY_ACTUAL_SKIN")
        from mathutils import Vector
        centroid=sum(verts,Vector())/len(verts)
        extent=max((v-centroid).length for v in verts)
        return tuple(float(x) for x in centroid), float(extent), len(verts)
    finally:
        evaluated.to_mesh_clear()

def glb_info(path):
    raw=path.read_bytes()
    assert len(raw)>96 and raw[:4]==b"glTF"
    magic,version,total=struct.unpack_from("<4sII",raw,0)
    assert version==2 and total==len(raw),"malformed GLB header"
    length,chunk=struct.unpack_from("<I4s",raw,12)
    assert chunk==b"JSON" and 20+length<=len(raw)
    doc=json.loads(raw[20:20+length].decode("utf-8").rstrip("\x00 "))
    assert doc.get("animations") and doc.get("skins") and doc.get("meshes")
    anim=doc["animations"][0]
    assert anim.get("channels") and anim.get("samplers")
    sample_types=[x["interpolation"] for x in anim["samplers"]]
    mesh_names=[m.get("name","") for m in doc["meshes"]]
    node_names=[n.get("name","") for n in doc.get("nodes",[])]
    counts=[doc["accessors"][x["input"]]["count"] for x in anim["samplers"]]
    assert min(counts)>=2
    return {"sha256":hashlib.sha256(raw).hexdigest(),
            "byte_length":len(raw),"animation_channels":len(anim["channels"]),
            "sampler_interpolations":sample_types,"sample_counts":counts,
            "skin_count":len(doc["skins"]),"mesh_count":len(doc["meshes"]),
            "glb_mesh_names":mesh_names,"glb_node_names":node_names}

def run(root,lane,export_out=None):
    import bpy
    from mathutils import Vector
    import probe as vsource
    assert bpy.app.version>=(4,5,0)
    root=root.resolve()
    vmd=vsource.upstream(root)
    curve=vsource.CURVE if lane=="nonlinear" else vsource.LINEAR
    with tempfile.TemporaryDirectory(prefix="motion-r3-original-only-") as tmp:
        temp=pathlib.Path(tmp)
        source=temp/"original.vmd";export=temp/"derived.glb"
        vsource.authored(vmd,source,curve)
        checked=vsource.loaded(vmd,source)
        vsource.check_strict_semantics(checked,curve)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sys.path.insert(0,str(root))
        from mmd_tools.core.vmd.importer import VMDImporter
        ad=bpy.data.armatures.new("R3_source_original")
        rig=bpy.data.objects.new("R3_source_original_rig",ad)
        bpy.context.scene.collection.objects.link(rig)
        bpy.context.view_layer.objects.active=rig
        rig.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        bone=ad.edit_bones.new(vsource.NAME); bone.head=(0,0,0);bone.tail=(0,0,.5)
        bpy.ops.object.mode_set(mode="OBJECT")
        rig.pose.bones[vsource.NAME].rotation_mode="QUATERNION"
        mesh=bpy.data.meshes.new("R3_original_quad")
        mesh.from_pydata([(0,0,0),(.2,0,0),(.2,.2,0),(0,.2,0)],[],[(0,1,2,3)])
        ob=bpy.data.objects.new("R3_original_skin",mesh)
        bpy.context.scene.collection.objects.link(ob)
        grp=ob.vertex_groups.new(name=vsource.NAME)
        grp.add([0,1,2,3],1.0,"REPLACE")
        mod=ob.modifiers.new("R3_actual_ARMATURE","ARMATURE");mod.object=rig
        bpy.context.scene.frame_set(0)
        assert bpy.context.scene.frame_current==0
        VMDImporter(str(source),scale=1.0,frame_margin=0).assign(rig)
        assert rig.animation_data and rig.animation_data.action
        ticks=[0.0,3.5,7.5,11.25,15.0,18.75,22.5,26.5,30.0]
        before=[skin_state(bpy,ob,t) for t in ticks]
        assert (Vector(before[-1][0])-Vector(before[0][0])).length>.5
        for c,e in zip(ticks,before):
            alpha=vsource.curve_at(c/30.0,curve)
            span=Vector(before[-1][0])-Vector(before[0][0])
            progress=(Vector(e[0])-Vector(before[0][0])).dot(span)/span.length_squared
            assert abs(progress-alpha)<1e-4, ("input VMD/skin mismatch",c,progress,alpha)
        bpy.ops.object.select_all(action="DESELECT")
        rig.select_set(True);ob.select_set(True)
        bpy.context.view_layer.objects.active=rig
        source_selection=[(x.name,x.type,len(x.data.vertices) if x.type=="MESH" else 0,x.select_get()) for x in bpy.data.objects]
        print("R3_PREEXPORT_SOURCE_SELECTION",json.dumps(source_selection,sort_keys=True),flush=True)
        result=bpy.ops.export_scene.gltf(filepath=str(export),export_format="GLB",
             use_selection=True,export_animations=True,export_force_sampling=True,
             export_frame_step=1,export_skins=True,export_morph=True)
        assert "FINISHED" in result and export.is_file()
        glb=glb_info(export)
        # Imported binary contains no VMD source 4-channel Bezier or property IK semantics.
        assert all(x in ("LINEAR","STEP","CUBICSPLINE") for x in glb["sampler_interpolations"])
        bpy.ops.wm.read_factory_settings(use_empty=True)
        result=bpy.ops.import_scene.gltf(filepath=str(export))
        assert "FINISHED" in result
        meshes=[o for o in bpy.data.objects if o.type=="MESH"]
        rigs=[o for o in bpy.data.objects if o.type=="ARMATURE"]
        assert len(meshes)>=1 and len(rigs)>=1,("GLB mesh or armature missing",len(meshes),len(rigs))
        imported_inventory=[(x.name,x.type,len(x.data.vertices) if x.type=="MESH" else 0,[m.type for m in x.modifiers],len(x.vertex_groups) if x.type=="MESH" else 0) for x in bpy.data.objects]
        print("R3_IMPORTED_INVENTORY",json.dumps(imported_inventory,sort_keys=True),flush=True)
        # Do not choose a random mesh by vertex count: this previously selected
        # an unskinned 42-vertex Icosphere rather than the source quad.
        candidates=[o for o in meshes if any(m.type=="ARMATURE" for m in o.modifiers)]
        if len(candidates)!=1:
            print("R3_ACTUAL_GLTF_MESH_BINDING_REJECT",json.dumps({"skinned_candidates":[o.name for o in candidates],"mesh_inventory":imported_inventory,"glb":glb},sort_keys=True),flush=True)
            raise AssertionError("GLB roundtrip has no unique actually skinned imported mesh")
        obj=candidates[0]
        rig2=rigs[0]
        assert rig2.animation_data and rig2.animation_data.action,"GLB imported animation lost"
        # Blender glTF-importer typically starts animation at 1 rather than VMD at 0;
        # discover the actual imported action frame range and report exact origin.
        first=float(rig2.animation_data.action.frame_range[0])
        assert first in (0.0,1.0),("unsupported imported GLB timebase",first)
        after=[skin_state(bpy,obj,t+first) for t in ticks]
        bs=Vector(before[0][0]);as_=Vector(after[0][0])
        motion_baseline=Vector(before[-1][0])-bs
        motion_imported=Vector(after[-1][0])-as_
        # Preserve original strict failed gate; print a bounded source-only diagnostic
        # before it. First actual GHA #44040646685 was RED in both variants.
        diag={"native_before_start":before[0],"native_before_end":before[-1],
              "imported_after_start":after[0],"imported_after_end":after[-1],
              "source_motion":motion_baseline.length,
              "imported_motion":motion_imported.length,
              "imported_rig_bones":[b.name for b in rig2.pose.bones],
              "imported_object":obj.name,
              "object_modifiers":[m.type for m in obj.modifiers],
              "imported_action_frame_range":list(rig2.animation_data.action.frame_range),
              "glb":glb}
        print("R3_DIAGNOSTIC_SOURCE_SAFE",json.dumps(diag,sort_keys=True),flush=True)
        assert motion_baseline.length>.5 and motion_imported.length>.5,"GLB frozen skin"
        max_relative=0.0
        max_intrinsic=0.0
        errors={}
        for tick,b,a in zip(ticks,before,after):
            bdisp=Vector(b[0])-bs;adisp=Vector(a[0])-as_
            residual=(adisp-bdisp).length
            max_relative=max(max_relative,residual)
            # Compare shape-independent centroid path; original+imported both evaluated mesh.
            errors[str(tick)]=residual
            max_intrinsic=max(max_intrinsic,abs(a[1]-b[1]))
        report={"schema":"scp.motion.r3.native-vmd-glb-reimport.v1",
                "status":"PASS_SYNTHETIC_NATIVE_GLTF_ANIMATION_ROUNDTRIP" if max_relative<=.015 else "FAIL_GLTF_REIMPORT_MOTION_DRIFT",
                "lane":lane,"blender":bpy.app.version_string,
                "mmd_tools_commit":vsource.UPSTREAM,
                "original_vmd_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
                "glb_metadata":glb,"source_sample_frames":ticks,
                "gltf_import_frame_origin":first,
                "source_evaluated_mesh_vertices":before[0][2],
                "import_evaluated_mesh_vertices":after[0][2],
                "max_relative_centroid_motion_error":max_relative,
                "max_centroid_error_per_tick":errors,
                "max_surface_extent_change":max_intrinsic,
                "source_vmd_interpolation_controls":"NOT_PRESERVED_AS_VMD_CONTROLS",
                "source_vmd_morph_keyframes":"NOT_BOUND_TO_GLTF_SHAPE_KEYS",
                "source_vmd_foot_ik_switches":"NOT_BOUND_TO_GLTF_IK",
                "native_mmd_runtime":"NOT_RUN",
                "MPFB_MHR_real_human":"NOT_RUN",
                "R009_film":"HOLD"}
        print(json.dumps(report,sort_keys=True),flush=True)
        if max_relative>.015: fail("GLB reimport drift >0.015 blender units")
        assert len(after)>0
        if export_out is not None:
            # The child independent-engine qualification consumes a disposable GLB
            # only after the complete Blender native roundtrip has passed.
            runner_temp=pathlib.Path(os.environ.get('RUNNER_TEMP','')).resolve()
            output=export_out.resolve()
            assert runner_temp.is_dir() and runner_temp in output.parents, 'Godot HIL output outside ephemeral runner temp'
            with output.open('xb') as sink:
                sink.write(export.read_bytes())
            assert hashlib.sha256(output.read_bytes()).hexdigest()==glb['sha256']
            print('R3_EPHEMERAL_GLTF_FOR_INDEPENDENT_ENGINE',json.dumps({'sha256':glb['sha256'],'bytes':output.stat().st_size},sort_keys=True),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",type=pathlib.Path,required=True)
    p.add_argument("--lane",choices=("nonlinear","linear"),required=True)
    p.add_argument("--export-out",type=pathlib.Path,default=None,help="one exclusively new GLB path under RUNNER_TEMP; private scratch only")
    a=p.parse_args()
    try:run(a.upstream,a.lane,a.export_out)
    except BaseException:
        traceback.print_exc()
        sys.stdout.flush();sys.stderr.flush();os._exit(1)
    sys.stdout.flush();sys.stderr.flush();os._exit(0)
