"""Original 3D weighted two-avatar Blender -> GLB -> fresh Blender numeric qualification.

Builds *actual* two-bone weighted deforming meshes with nonplanar vertices,
animated quaternion pose and one-to-one reimport vertex correspondence by
unique rest-space geometry. Does not use real people, media or private source.
"""
import argparse,hashlib,json,math
from pathlib import Path
import bpy
from mathutils import Quaternion, Vector

SOURCE="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
FRAMES=(0,12,24,36,48,60,71)
FPS=12


def analytic_ik(start,end,pole,u=.60,l=.60):
    """Original double-precision analytic 3D two-link solve.

    Blender mathutils Vector is float32: using it for the 1e-8 analytic
    segment invariant creates an artificial pre-export red. Evaluate source
    geometry in Python float64, then convert once to Blender Vector. Native
    bone tails are independently checked against the fixed 1e-3 gate.
    """
    a=tuple(float(x) for x in start)
    b=tuple(float(x) for x in end)
    po=tuple(float(x) for x in pole)
    direction=tuple(b[i]-a[i] for i in range(3))
    d=math.sqrt(math.fsum(x*x for x in direction))
    if not (abs(u-l)+1e-8<d<u+l-1e-8):
        raise ValueError("W16C_TARGET_OUTSIDE_STRICT_REACH")
    axis=tuple(x/d for x in direction)
    polevec=tuple(po[i]-a[i] for i in range(3))
    parallel=math.fsum(polevec[i]*axis[i] for i in range(3))
    p=tuple(polevec[i]-axis[i]*parallel for i in range(3))
    plen=math.sqrt(math.fsum(x*x for x in p))
    if plen<1e-8:raise ValueError("W16C_DEGENERATE_POLE")
    side=tuple(x/plen for x in p)
    along=(u*u-l*l+d*d)/(2*d)
    height=math.sqrt(max(0.0,u*u-along*along))
    k=tuple(a[i]+axis[i]*along+side[i]*height for i in range(3))
    if abs(math.dist(k,a)-u)>1e-8 or abs(math.dist(k,b)-l)>1e-8:
        raise ValueError("W16C_DOUBLE_PRECISION_IK_SEGMENT_LENGTH")
    return Vector(k)


def add_actor(name,x,profile,phase):
    data=bpy.data.armatures.new(name+"_ArmatureData")
    arm=bpy.data.objects.new(name+"_Skeleton",data)
    bpy.context.scene.collection.objects.link(arm)
    arm.location=(x,0,0)
    bpy.context.view_layer.objects.active=arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    parent=data.edit_bones.new("upper")
    parent.head=(0,0,1.40);parent.tail=(0,0,.80)
    child=data.edit_bones.new("lower")
    child.head=(0,0,.80);child.tail=(0,0,.20)
    child.parent=parent;child.use_connect=True
    bpy.ops.object.mode_set(mode="OBJECT")
    for b in arm.pose.bones:b.rotation_mode="QUATERNION"
    verts=[];faces=[]
    levels=[1.34,1.12,.91,.80,.69,.48,.27]
    for z in levels:
        # deliberately nonplanar and asymmetric per-vertex depth.
        verts.extend([(-.10,-.07,z),(.08,-.065,z),
                      (.095,.085,z),(-.085,.080,z)])
    for r in range(len(levels)-1):
        for c in range(4):
            a=r*4+c; b=r*4+(c+1)%4
            d=(r+1)*4+c; e=(r+1)*4+(c+1)%4
            faces.extend([(a,d,b),(b,d,e)])
    mesh=bpy.data.meshes.new(name+"_source_mesh")
    mesh.from_pydata(verts,[],faces);mesh.update()
    for face in mesh.polygons:face.use_smooth=True
    obj=bpy.data.objects.new(name+"_SkinnedMesh",mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent=arm
    upper=obj.vertex_groups.new(name="upper")
    lower=obj.vertex_groups.new(name="lower")
    for k,z in enumerate(levels):
        u=1 if z>=.91 else (0 if z<=.48 else (.50 if z==.80 else .25))
        l=1-u
        if u>0:upper.add(list(range(k*4,k*4+4)),u,"REPLACE")
        if l>0:lower.add(list(range(k*4,k*4+4)),l,"REPLACE")
    mod=obj.modifiers.new("OriginalArmatureSkin","ARMATURE");mod.object=arm
    arm["source_rights"]=SOURCE
    obj["source_rights"]=SOURCE
    # W16-C replaces earlier unrelated sinusoidal joint keyframes with explicit
    # analytic 3D two-bone IK, moving original roots, and a qualified native
    # parent-relative quaternion conversion. Foot/sole physics is NOT claimed.
    side=1 if name=="CobaltOriginal" else -1
    if profile=="outward":side= -side
    rest_u=data.bones["upper"].matrix_local.to_quaternion()
    rest_l=data.bones["lower"].matrix_local.to_quaternion()
    src_axis=Vector((0,0,-1))
    for f in FRAMES:
        bpy.context.scene.frame_set(f)
        offset=side*.27*f/71.
        arm.location=(x+offset,0,0)
        if f==0:
            qu=Quaternion((1,0,0,0))
            ql=Quaternion((1,0,0,0))
        else:
            hip=Vector((x+offset,0,1.40))
            # Explicit artificial held-target early segment; then sampled swing.
            # This is a motion task target, not a recognized shoe/sole trace.
            lead=max(0.,(f-36.)/35.)
            end=Vector((x+side*.27*lead,0,.24+.04*lead))
            pole=hip+Vector((side*.5,.35,-.55))
            knee=analytic_ik(hip,end,pole)
            world_upper=src_axis.rotation_difference((knee-hip).normalized())
            world_lower=src_axis.rotation_difference((end-knee).normalized())
            # Convert world-aligned segment orientations to actual Blender
            # bone-rest-local and hierarchical lower-child rotations.
            qu=rest_u.inverted()@world_upper@rest_u
            ql=rest_l.inverted()@world_upper.inverted()@world_lower@rest_l
        arm.pose.bones["upper"].rotation_quaternion=qu
        arm.pose.bones["lower"].rotation_quaternion=ql
        bpy.context.view_layer.update()
        if f:
            observed_knee=arm.matrix_world@arm.pose.bones["upper"].tail
            observed_end=arm.matrix_world@arm.pose.bones["lower"].tail
            knee_error=(observed_knee-knee).length
            end_error=(observed_end-end).length
            if knee_error>1e-3 or end_error>1e-3:
                print("W16C_FIRST_IK_FK_FAILURE",json.dumps({
                    "actor":name,"frame":f,"knee_error":knee_error,
                    "ankle_error":end_error,"expected_knee":list(knee),
                    "actual_knee":list(observed_knee),
                    "expected_ankle":list(end),"actual_ankle":list(observed_end)
                }),flush=True)
                raise ValueError("W16C_IK_TO_NATIVE_RIG_FK_MISMATCH")
        arm.keyframe_insert(data_path="location",frame=f)
        arm.pose.bones["upper"].keyframe_insert(data_path="rotation_quaternion",frame=f)
        arm.pose.bones["lower"].keyframe_insert(data_path="rotation_quaternion",frame=f)
    return arm,obj

def evaluated_points(obj,frame):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    deps=bpy.context.evaluated_depsgraph_get()
    ev=obj.evaluated_get(deps)
    mesh=ev.to_mesh()
    try:return [tuple(ev.matrix_world@v.co) for v in mesh.vertices]
    finally:ev.to_mesh_clear()

def min_pair_match(reference,candidate):
    # Fail-closed unique one-to-one correspondence; set matching avoids assuming
    # glTF importer retains vertex indices after normal/triangulation conversion.
    if len(reference)!=len(candidate):raise ValueError("GLB_VERTEX_COUNT_OR_SPLIT_CHANGED")
    remaining=set(range(len(candidate)))
    mapping=[]
    for a in reference:
        best=min(remaining,key=lambda idx:math.dist(a,candidate[idx]))
        error=math.dist(a,candidate[best])
        if error>2e-5:
            print("W14_REIMPORT_FIRST_FRAME_MISMATCH",json.dumps({
                "original":a,"closest_imported":candidate[best],
                "error":error,
                "source_count":len(reference),
                "import_count":len(candidate),
                "first_original":reference[:3],
                "first_imported":candidate[:3],
            }),flush=True)
            raise ValueError("GLB_REST_VERTEX_CORRESPONDENCE_FAIL")
        mapping.append(best);remaining.remove(best)
    if remaining:raise ValueError("NON_BIJECTIVE_VERTEX_MAP")
    return mapping

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--profile",choices=["forward","outward"],required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.render.fps=FPS
    scene.frame_start=0;scene.frame_end=71
    assets={}
    for i,(name,x) in enumerate([("CobaltOriginal",-1.65),("MarigoldOriginal",1.65)]):
        arm,obj=add_actor(name,x,args.profile,i*.73)
        assets[name]=(arm,obj)
    # Fully editable source scene includes explicit camera, not source-private media.
    camera_data=bpy.data.cameras.new("OriginalSyntheticCamera")
    camera_data.type="ORTHO";camera_data.ortho_scale=5.5
    camera=bpy.data.objects.new("OriginalSyntheticCamera",camera_data)
    scene.collection.objects.link(camera)
    camera.location=(0,-7,2.0)
    look=Vector((0,0,.75))-camera.location
    camera.rotation_euler=look.to_track_quat("-Z","Y").to_euler()
    scene.camera=camera
    scene.render.engine="BLENDER_WORKBENCH"
    scene.render.resolution_x=320
    scene.render.resolution_y=180
    scene.render.resolution_percentage=100
    native={name:{str(f):evaluated_points(obj,f) for f in FRAMES} for name,(_,obj) in assets.items()}
    if any(len(v["0"])!=28 for v in native.values()):raise ValueError("ORIGINAL_MESH_INDEX_COUNT")
    for name,(_,obj) in assets.items():
        vertex_assignments=[len(vertex.groups) for vertex in obj.data.vertices]
        if min(vertex_assignments)<1 or max(vertex_assignments)<2:
            raise ValueError("EXPECTED_SINGLE_AND_DUAL_WEIGHTED_VERTICES")
    # Recalculate all world transforms for saved scene.
    scene.frame_set(0)
    blend=out/"original_two_weighted_3d_characters.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
    glb=out/"original_two_weighted_3d_characters.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb.resolve()),export_format="GLB",export_animations=True)
    if glb.stat().st_size<1000 or blend.stat().st_size<10000:
        raise ValueError("MISSING_REAL_GLTF_OR_EDITABLE_BLEND")
    # Native H.264 output is a separate viewability witness, NOT a gait/contact pass.
    scene.render.image_settings.file_format="FFMPEG"
    scene.render.ffmpeg.format="MPEG4"
    scene.render.ffmpeg.codec="H264"
    scene.render.ffmpeg.constant_rate_factor="HIGH"
    scene.render.filepath=str((out/"original_integrated_3d_ik_preview.mp4").resolve())
    bpy.ops.render.render(animation=True)
    if not (out/"original_integrated_3d_ik_preview.mp4").exists() or (out/"original_integrated_3d_ik_preview.mp4").stat().st_size<1000:
        raise ValueError("W16C_NATIVE_H264_MISSING")
    # Independent native readback from freshly imported GLB, not same in-memory
    # object, evaluated through Blender's imported skinning modifier.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps=FPS
    bpy.ops.import_scene.gltf(filepath=str(glb.resolve()))
    imported={}
    for obj in bpy.data.objects:
        if obj.type=="MESH" and any(m.type=="ARMATURE" for m in obj.modifiers):
            imported[obj.name.split("_SkinnedMesh")[0]]=obj
    if set(imported)!=set(assets):raise ValueError("GLB_SKIN_OBJECT_NAMES_OR_COUNTS")
    if len([x for x in bpy.data.objects if x.type=="ARMATURE"])!=2:
        raise ValueError("GLB_ARMATURE_MISSING")
    if not bpy.data.actions:raise ValueError("GLB_IMPORTED_ANIMATION_MISSING")
    # The bpy 4.5 glTF importer can retain named Action assets without assigning
    # their layered ActionSlot to the imported armature's live animation_data.
    # Bind ONLY exact actor-name matches and require an OBJECT slot, never
    # silently evaluate rest pose as a successful animated skin import.
    for name in assets:
        arm=bpy.data.objects.get(name+"_Skeleton")
        if arm is None or arm.type!="ARMATURE":raise ValueError("GLB_ACTOR_ARMATURE_MISSING")
        action=bpy.data.actions.get(arm.name+"Action")
        if action is None:raise ValueError("GLB_ACTOR_SPECIFIC_ACTION_MISSING")
        slots=[s for s in action.slots if s.target_id_type=="OBJECT"]
        if len(slots)!=1:raise ValueError("GLB_ACTION_SLOT_MISSING_OR_AMBIGUOUS")
        data=arm.animation_data_create()
        if data.action is not None and data.action is not action:
            raise ValueError("GLB_DIFFERENT_ACTION_ALREADY_BOUND")
        data.action=action
        data.action_slot=slots[0]
        if data.action is not action or data.action_slot!=slots[0]:
            raise ValueError("GLB_CORRECT_ACTION_NOT_LIVE")
        print("W14_EXACT_GLTF_ACTION_SLOT_BOUND",name,action.name,slots[0].identifier,flush=True)
    max_err=0.
    minimum_motion=math.inf
    imported_count=0
    for name,obj in imported.items():
        rest=evaluated_points(obj,FRAMES[0])
        mapping=min_pair_match(native[name][str(FRAMES[0])],rest)
        moved=0.
        for f in FRAMES:
            actual=evaluated_points(obj,f)
            expected=native[name][str(f)]
            if len(actual)!=len(mapping):raise ValueError("GLB_FRAME_VERTEX_TOPOLOGY_CHANGED")
            for src_idx,dest_idx in enumerate(mapping):
                e=math.dist(actual[dest_idx],expected[src_idx])
                max_err=max(max_err,e)
                if e>5e-4:
                    print("W14_ANIMATION_PARITY_FIRST_FAILURE",json.dumps({
                        "actor":name,"frame":f,"src_vertex":src_idx,
                        "dst_vertex":dest_idx,"expected":expected[src_idx],
                        "actual":actual[dest_idx],"error":e,
                        "max_before":max_err,
                        "imported_scene_fps":bpy.context.scene.render.fps,
                        "action_names":[a.name for a in bpy.data.actions],
                        "mesh_armature": [(m.object.name if m.object else "NONE") for m in obj.modifiers if m.type=="ARMATURE"],
                        "parent":obj.parent.name if obj.parent else None,
                        "pose_upper": ([float(v) for v in obj.parent.pose.bones["upper"].rotation_quaternion] if obj.parent and obj.parent.type=="ARMATURE" else None),
                        "parent_action": (obj.parent.animation_data.action.name if obj.parent and obj.parent.animation_data and obj.parent.animation_data.action else None),
                    }),flush=True)
                    raise ValueError("GLB_REIMPORT_WEIGHTED_3D_VERTEX_PARITY_FAIL")
            moved=max(moved,max(math.dist(a,b) for a,b in zip(expected,native[name]["0"])))
            imported_count+=len(mapping)
        minimum_motion=min(minimum_motion,moved)
    if minimum_motion<.02:raise ValueError("STATIC_OR_DETACHED_WEIGHTED_SKIN")
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    receipt={"schema":"scp.walk_w14_original_weighted_3d_glb.v1",
             "status":"PASS_BLENDER_NATIVE_TWO_WEIGHTED_3D_AND_GLB_REIMPORT",
             "source_rights":SOURCE,"profile":args.profile,
             "actors":2,"bones_per_actor":2,"vertices_per_actor":28,
             "source_frame_numbers":list(FRAMES),"fps":FPS,
             "imported_evaluated_vertex_observations":imported_count,
             "maximum_world_vertex_error":max_err,
             "minimum_actor_deformation":minimum_motion,
             "rest_vertex_correspondence":"ONE_TO_ONE_BY_SPATIAL_MATCH_AT_SOURCE_T0",
             "quat_representation":"Blender WXYZ native; glTF XYZW serialized",
             "true_xyz_deformation":True,"weighted_mesh":True,
             "source_motion":"ORIGINAL_EXPLICIT_ANALYTIC_3D_IK_ROOT_WALK_NOT_MEASURED_GAIT",
             "body_contact":"NOT_QUALIFIED","character_identity":"NOT_APPLICABLE",
             "independent_non_blender_reader":"NOT_YET_QUALIFIED",
             "blend_sha256":sha(blend),"glb_sha256":sha(glb),
             "video_sha256":sha(out/"original_integrated_3d_ik_preview.mp4"),
             "video_scope":"NATIVE_H264_PREVIEW_NOT_CONTACT_OR_IDENTITY_ACCEPTANCE"}
    # Independent non-Blender W15 reader must compare its own mathematical
    # LBS results with original source scene world vertices, not merely the
    # imported Blender scene or a self-reported parity summary.
    truth={"schema":"scp.walk_w15_source_truth.v1",
           "glb_sha256":sha(glb),"source_rights":SOURCE,
           "frames":list(FRAMES),
           "world_vertices":{str(f):{name:native[name][str(f)] for name in assets} for f in FRAMES}}
    (out/"native_source_vertex_truth.json").write_text(json.dumps(truth,sort_keys=True,indent=2)+"\n")
    (out/"native_3d_skin_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print("W14_WEIGHTED_TWO_AVATAR_GLB_PASS",json.dumps(receipt,sort_keys=True))
if __name__=="__main__":main()
